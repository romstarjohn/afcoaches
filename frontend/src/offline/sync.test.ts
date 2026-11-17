import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthRequiredError, NetworkError } from '../api/client'
import { LocalDb } from './db'
import { enqueue, failedItems, pendingCount } from './outbox'
import { backoffMs, SyncEngine, type PushFn, type PushResult } from './sync'

let db: LocalDb
let clock = 1_000_000

function setOnline(value: boolean) {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(value)
}

const applyAll: PushFn = async (ops) => ({ results: ops.map((o) => ({ op_id: o.op_id, status: 'applied' })) })

beforeEach(async () => {
  db = new LocalDb(`test-${crypto.randomUUID()}`)
  await db.open()
  clock = 1_000_000
  setOnline(true)
})

afterEach(async () => {
  await db.delete()
})

const engine = (push: PushFn) => new SyncEngine(push, db, () => clock)

describe('outbox', () => {
  it('coalesces edits of the same record into one pending operation', async () => {
    const first = await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert', data: { v: 1 } }, db)
    const second = await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert', data: { v: 2 } }, db)
    await enqueue({ entity: 'note', recordId: 'r2', action: 'upsert', data: { v: 1 } }, db)

    expect(await pendingCount(db)).toBe(2)
    expect(second.opId).not.toBe(first.opId)
    const r1 = await db.outbox.where('opId').equals(second.opId).first()
    expect(r1?.data).toEqual({ v: 2 })
  })
})

describe('SyncEngine', () => {
  it('pushes pending operations and removes applied ones', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert', data: { v: 1 } }, db)
    const push = vi.fn(applyAll)
    await engine(push).flush()

    expect(push).toHaveBeenCalledOnce()
    expect(push.mock.calls[0][0][0]).toMatchObject({ entity: 'note', id: 'r1', action: 'upsert', data: { v: 1 } })
    expect(await pendingCount(db)).toBe(0)
  })

  it('does nothing while offline and keeps data', async () => {
    setOnline(false)
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert' }, db)
    const push = vi.fn(applyAll)
    const e = engine(push)
    await e.flush()

    expect(push).not.toHaveBeenCalled()
    expect(e.state).toBe('offline')
    expect(await pendingCount(db)).toBe(1)
  })

  it('moves refused operations aside and never retries them automatically', async () => {
    await enqueue({ entity: 'note', recordId: 'ok', action: 'upsert' }, db)
    await enqueue({ entity: 'note', recordId: 'bad', action: 'upsert' }, db)
    await enqueue({ entity: 'note', recordId: 'locked', action: 'upsert' }, db)
    const push: PushFn = async (ops) => ({
      results: ops.map((o): PushResult => {
        if (o.id === 'bad') return { op_id: o.op_id, status: 'rejected', error: 'not_allowed' }
        if (o.id === 'locked') return { op_id: o.op_id, status: 'conflict', error: 'locked' }
        return { op_id: o.op_id, status: 'applied' }
      }),
    })
    await engine(push).flush()

    expect(await pendingCount(db)).toBe(0)
    const failed = await failedItems(db)
    expect(failed.map((f) => [f.recordId, f.lastError])).toEqual([
      ['bad', 'not_allowed'],
      ['locked', 'locked'],
    ])
  })

  it('backs off after network errors and retries when due', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert' }, db)
    let fail = true
    const push = vi.fn<PushFn>(async (ops) => {
      if (fail) throw new NetworkError('down')
      return applyAll(ops)
    })
    const e = engine(push)

    await e.flush()
    expect(e.state).toBe('error')
    const item = await db.outbox.toCollection().first()
    expect(item?.attempts).toBe(1)
    expect(item?.nextAttemptAt).toBe(clock + backoffMs(1))

    fail = false
    await e.flush() // not due yet
    expect(push).toHaveBeenCalledTimes(1)

    clock += backoffMs(1)
    await e.flush()
    expect(push).toHaveBeenCalledTimes(2)
    expect(await pendingCount(db)).toBe(0)
  })

  it('manual retry ignores the backoff delay', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert' }, db)
    let fail = true
    const push = vi.fn<PushFn>(async (ops) => {
      if (fail) throw new NetworkError('down')
      return applyAll(ops)
    })
    const e = engine(push)
    await e.flush()
    fail = false
    await e.flush({ force: true })
    expect(push).toHaveBeenCalledTimes(2)
    expect(await pendingCount(db)).toBe(0)
  })

  it('keeps everything when the session expired', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert' }, db)
    const e = engine(async () => {
      throw new AuthRequiredError(403, { detail: 'Authentication credentials were not provided.' })
    })
    await e.flush()

    expect(e.state).toBe('auth-required')
    const item = await db.outbox.toCollection().first()
    expect(item).toMatchObject({ status: 'pending', attempts: 0 })
  })

  it('does not drop an edit made while the previous version was in flight', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert', data: { v: 1 } }, db)
    const push: PushFn = async (ops) => {
      await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert', data: { v: 2 } }, db)
      return applyAll(ops)
    }
    // The ack for v1 must not delete v2, which got a new opId while v1 was in flight.
    await engine(push).flush()
    const remaining = await db.outbox.toArray()
    expect(remaining).toHaveLength(1)
    expect(remaining[0]).toMatchObject({ status: 'pending', data: { v: 2 } })
  })

  it('shares one run between concurrent flush calls', async () => {
    await enqueue({ entity: 'note', recordId: 'r1', action: 'upsert' }, db)
    const push = vi.fn(applyAll)
    const e = engine(push)
    await Promise.all([e.flush(), e.flush(), e.flush()])
    expect(push).toHaveBeenCalledOnce()
  })

  it('caps the backoff at five minutes', () => {
    expect(backoffMs(1)).toBe(2000)
    expect(backoffMs(20)).toBe(5 * 60_000)
  })
})
