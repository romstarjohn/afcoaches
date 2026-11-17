import { liveQuery } from 'dexie'
import { useEffect, useState, useSyncExternalStore } from 'react'
import { pendingCount } from './outbox'
import { syncEngine, type SyncState } from './sync'
import { db } from './db'

export function useOnline() {
  return useSyncExternalStore(
    (notify) => {
      window.addEventListener('online', notify)
      window.addEventListener('offline', notify)
      return () => {
        window.removeEventListener('online', notify)
        window.removeEventListener('offline', notify)
      }
    },
    () => navigator.onLine,
  )
}

export function useSyncState(): SyncState {
  return useSyncExternalStore(
    (notify) => {
      const off = syncEngine.subscribe(notify)
      return () => void off()
    },
    () => syncEngine.state,
  )
}

/** Live counts of unsynced and refused changes. */
export function useOutboxCounts() {
  const [counts, setCounts] = useState({ pending: 0, failed: 0 })
  useEffect(() => {
    const subscription = liveQuery(async () => ({
      pending: await pendingCount(),
      failed: await db.outbox.where('status').equals('failed').count(),
    })).subscribe({ next: setCounts, error: () => setCounts({ pending: 0, failed: 0 }) })
    return () => subscription.unsubscribe()
  }, [])
  return counts
}
