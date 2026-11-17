import Dexie, { type EntityTable } from 'dexie'

/**
 * Local database (IndexedDB). Holds data the user saved while offline until it is synced.
 * Feature tables (e.g. cached plans, feedback drafts) are added in later schema versions.
 *
 * Security: IndexedDB is not encrypted. Only data the user needs offline goes here, and everything is
 * wiped on logout via clearLocalData().
 */

export type SyncAction = 'upsert' | 'delete'

export interface OutboxItem {
  seq?: number
  /** Unique per attempt-able change; the server echoes it back in the push result. */
  opId: string
  entity: string
  /** Client-generated UUID of the record: makes server writes idempotent. */
  recordId: string
  action: SyncAction
  data: Record<string, unknown>
  clientUpdatedAt: string
  /** pending: will be pushed · failed: rejected/conflict, needs the user's attention, never auto-retried */
  status: 'pending' | 'failed'
  attempts: number
  nextAttemptAt: number
  lastError?: string
}

export class LocalDb extends Dexie {
  outbox!: EntityTable<OutboxItem, 'seq'>

  constructor(name = 'coachsurmesure') {
    super(name)
    this.version(1).stores({
      outbox: '++seq, &opId, [entity+recordId], status, nextAttemptAt',
    })
  }
}

export const db = new LocalDb()

/** Wipe everything stored on the device (logout, account switch). */
export async function clearLocalData(target: LocalDb = db) {
  await target.delete()
  await target.open()
  if (typeof caches !== 'undefined') {
    // Only our runtime caches; the precached app shell is managed by the service worker.
    const keys = await caches.keys()
    await Promise.all(keys.filter((k) => k.startsWith('csm-data')).map((k) => caches.delete(k)))
  }
}

/** Ask the browser not to evict our offline data under storage pressure (best effort). */
export async function requestPersistentStorage(): Promise<boolean> {
  if (!navigator.storage?.persist) return false
  if (await navigator.storage.persisted()) return true
  return navigator.storage.persist()
}
