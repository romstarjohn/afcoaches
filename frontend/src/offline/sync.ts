import { api, AuthRequiredError, NetworkError } from '../api/client'
import { db as defaultDb, type LocalDb, type OutboxItem } from './db'
import { onEnqueue } from './outbox'

export interface PushOperation {
  op_id: string
  entity: string
  id: string
  action: 'upsert' | 'delete'
  data: Record<string, unknown>
  client_updated_at: string
}

export interface PushResult {
  op_id: string
  status: 'applied' | 'conflict' | 'rejected'
  error?: string
}

export type PushFn = (operations: PushOperation[]) => Promise<{ results: PushResult[] }>

export type SyncState = 'idle' | 'syncing' | 'offline' | 'auth-required' | 'error'

const BATCH_SIZE = 50
const MAX_BACKOFF_MS = 5 * 60_000
const INTERVAL_MS = 60_000

export const defaultPush: PushFn = (operations) => api.post('/api/v1/sync/push', { operations })

export function backoffMs(attempts: number) {
  return Math.min(1000 * 2 ** attempts, MAX_BACKOFF_MS)
}

function toOperation(item: OutboxItem): PushOperation {
  return {
    op_id: item.opId,
    entity: item.entity,
    id: item.recordId,
    action: item.action,
    data: item.data,
    client_updated_at: item.clientUpdatedAt,
  }
}

/**
 * Pushes the outbox to the server whenever a connection is available.
 *
 * Triggers: start, enqueue, `online` event, app back in foreground, and every minute while online.
 * (Background Sync is not used: it does not exist on iOS, and installed PWAs sync on open anyway.)
 */
export class SyncEngine {
  private running: Promise<void> | null = null
  private timer: ReturnType<typeof setInterval> | null = null
  private cleanups: Array<() => void> = []
  private listeners = new Set<(state: SyncState) => void>()
  state: SyncState = 'idle'
  private readonly push: PushFn
  private readonly db: LocalDb
  private readonly now: () => number

  constructor(push: PushFn = defaultPush, db: LocalDb = defaultDb, now: () => number = Date.now) {
    this.push = push
    this.db = db
    this.now = now
  }

  subscribe(listener: (state: SyncState) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private setState(state: SyncState) {
    this.state = state
    this.listeners.forEach((l) => l(state))
  }

  start() {
    const trigger = () => void this.flush()
    const onVisible = () => document.visibilityState === 'visible' && trigger()
    window.addEventListener('online', trigger)
    window.addEventListener('offline', () => this.setState('offline'))
    document.addEventListener('visibilitychange', onVisible)
    const offEnqueue = onEnqueue(trigger)
    this.timer = setInterval(trigger, INTERVAL_MS)
    this.cleanups = [
      () => window.removeEventListener('online', trigger),
      () => document.removeEventListener('visibilitychange', onVisible),
      () => void offEnqueue(),
      () => this.timer && clearInterval(this.timer),
    ]
    trigger()
  }

  stop() {
    this.cleanups.forEach((c) => c())
    this.cleanups = []
  }

  /**
   * Push everything that is due. `force` (manual retry) ignores the backoff delay.
   * Concurrent calls share one run; other tabs are excluded via Web Locks.
   */
  flush({ force = false }: { force?: boolean } = {}): Promise<void> {
    if (!this.running) {
      const run = () => this.drain(force)
      const locked = navigator.locks?.request ? navigator.locks.request('csm-sync', run) : run()
      this.running = Promise.resolve(locked).finally(() => {
        this.running = null
      })
    }
    return this.running
  }

  private async drain(force: boolean) {
    if (!navigator.onLine) {
      this.setState('offline')
      return
    }
    this.setState('syncing')
    for (;;) {
      const due = await this.db.outbox
        .where('status')
        .equals('pending')
        .filter((i) => force || i.nextAttemptAt <= this.now())
        .sortBy('seq')
      const batch = due.slice(0, BATCH_SIZE)
      if (batch.length === 0) break

      let results: PushResult[]
      try {
        results = (await this.push(batch.map(toOperation))).results
      } catch (error) {
        if (error instanceof AuthRequiredError) {
          // Keep everything; data is pushed after the next login.
          this.setState('auth-required')
          return
        }
        await this.scheduleRetry(batch, error instanceof NetworkError ? error.message : 'unexpected')
        this.setState(navigator.onLine ? 'error' : 'offline')
        return
      }
      await this.applyResults(batch, results)
      if (batch.length < BATCH_SIZE) break
    }
    this.setState('idle')
  }

  private async applyResults(batch: OutboxItem[], results: PushResult[]) {
    const byOp = new Map(results.map((r) => [r.op_id, r]))
    await this.db.transaction('rw', this.db.outbox, async () => {
      for (const item of batch) {
        const result = byOp.get(item.opId)
        // Look up by opId: if the user edited the record meanwhile, the newer edit keeps a new opId.
        const current = await this.db.outbox.where('opId').equals(item.opId).first()
        if (!current?.seq) continue
        if (!result) {
          await this.db.outbox.update(current.seq, this.retryFields(current, 'missing_result'))
        } else if (result.status === 'applied') {
          await this.db.outbox.delete(current.seq)
        } else {
          await this.db.outbox.update(current.seq, { status: 'failed', lastError: result.error ?? result.status })
        }
      }
    })
  }

  private retryFields(item: OutboxItem, error: string): Partial<OutboxItem> {
    const attempts = item.attempts + 1
    return { attempts, nextAttemptAt: this.now() + backoffMs(attempts), lastError: error }
  }

  private async scheduleRetry(batch: OutboxItem[], error: string) {
    await this.db.transaction('rw', this.db.outbox, async () => {
      for (const item of batch) {
        const current = await this.db.outbox.where('opId').equals(item.opId).first()
        if (current?.seq) await this.db.outbox.update(current.seq, this.retryFields(current, error))
      }
    })
  }
}

export const syncEngine = new SyncEngine()
