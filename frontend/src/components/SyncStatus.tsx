import { useTranslation } from 'react-i18next'
import { useOnline, useOutboxCounts, useSyncState } from '../offline/hooks'
import { syncEngine } from '../offline/sync'

/** Always tells the user whether their data is safe on the device or already synced. */
export function SyncStatus() {
  const { t } = useTranslation()
  const online = useOnline()
  const state = useSyncState()
  const { pending, failed } = useOutboxCounts()

  const messages: string[] = []
  if (!online) messages.push(t('status.offline'))
  else if (state === 'auth-required') messages.push(t('status.authRequired'))
  else if (state === 'syncing') messages.push(t('status.syncing'))
  else if (state === 'error') messages.push(t('status.error'))
  if (pending > 0) messages.push(t('status.pending', { count: pending }))
  if (failed > 0) messages.push(t('status.failed', { count: failed }))

  const tone = failed > 0 || state === 'auth-required' || state === 'error' ? 'warn' : online ? 'ok' : 'offline'
  const canRetry = online && pending > 0 && (state === 'error' || state === 'idle')
  return (
    <div className={`sync-status sync-status--${tone}`} role="status" aria-live="polite">
      <span className="sync-status__dot" aria-hidden="true" />
      <span>{messages.length ? messages.join(' · ') : t('status.online')}</span>
      {canRetry && (
        <button type="button" className="button sync-status__retry" onClick={() => void syncEngine.flush({ force: true })}>
          {t('status.retry')}
        </button>
      )}
    </div>
  )
}
