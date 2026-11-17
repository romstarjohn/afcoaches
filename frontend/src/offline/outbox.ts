import { db as defaultDb, type LocalDb, type OutboxItem, type SyncAction } from './db'

export interface EnqueueInput {
  entity: string
  recordId: string
  action: SyncAction
  data?: Record<string, unknown>
}

type Listener = () => void
const listeners = new Set<Listener>()

/** Notified after every local write, so the sync engine can push immediately when online. */
export function onEnqueue(listener: Listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * Save a change locally. Several edits of the same record before the next sync are coalesced into one
 * operation (latest wins), so the outbox stays small after long offline periods.
 */
export async function enqueue(input: EnqueueInput, target: LocalDb = defaultDb): Promise<OutboxItem> {
  const item = await target.transaction('rw', target.outbox, async () => {
    const now = new Date().toISOString()
    const fresh: Omit<OutboxItem, 'seq'> = {
      opId: crypto.randomUUID(),
      entity: input.entity,
      recordId: input.recordId,
      action: input.action,
      data: input.data ?? {},
      clientUpdatedAt: now,
      status: 'pending',
      attempts: 0,
      nextAttemptAt: 0,
    }
    const existing = await target.outbox
      .where('[entity+recordId]')
      .equals([input.entity, input.recordId])
      .filter((i) => i.status === 'pending')
      .first()
    if (existing?.seq !== undefined) {
      // New opId: if the old version is in flight right now, its result will not delete this newer edit.
      await target.outbox.update(existing.seq, fresh)
      return { ...existing, ...fresh }
    }
    const seq = await target.outbox.add(fresh as OutboxItem)
    return { ...fresh, seq }
  })
  listeners.forEach((l) => l())
  return item
}

export async function pendingCount(target: LocalDb = defaultDb) {
  return target.outbox.where('status').equals('pending').count()
}

export async function failedItems(target: LocalDb = defaultDb) {
  return target.outbox.where('status').equals('failed').toArray()
}

/** User decided to drop a change the server refused. */
export async function discardFailed(seq: number, target: LocalDb = defaultDb) {
  await target.outbox.delete(seq)
}
