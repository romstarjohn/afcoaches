import { useTranslation } from 'react-i18next'
import { useRegisterSW } from 'virtual:pwa-register/react'
import { syncEngine } from '../offline/sync'

const UPDATE_CHECK_MS = 60 * 60_000

/** Asks before activating a new version, so nobody loses a half-filled form. */
export function UpdatePrompt() {
  const { t } = useTranslation()
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_url, registration) {
      // Installed apps can stay open for days: look for new versions hourly.
      if (registration) setInterval(() => void registration.update(), UPDATE_CHECK_MS)
    },
  })

  if (!needRefresh && !offlineReady) return null
  const applyUpdate = async () => {
    // Push unsynced changes first; anything left stays safely in IndexedDB across the reload.
    await syncEngine.flush().catch(() => undefined)
    await updateServiceWorker(true)
  }
  const close = () => {
    setNeedRefresh(false)
    setOfflineReady(false)
  }
  return (
    <div className="toast" role="alert">
      <span>{needRefresh ? t('pwa.updateAvailable') : t('pwa.offlineReady')}</span>
      {needRefresh && (
        <button type="button" className="button button--primary" onClick={() => void applyUpdate()}>
          {t('pwa.update')}
        </button>
      )}
      <button type="button" className="button" onClick={close}>
        {t('pwa.dismiss')}
      </button>
    </div>
  )
}
