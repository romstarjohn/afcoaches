import { useState, useSyncExternalStore } from 'react'
import { useTranslation } from 'react-i18next'
import {
  dismissInstallHint,
  getInstallPrompt,
  isIos,
  promptInstall,
  shouldOfferInstall,
  subscribeInstallPrompt,
} from '../pwa/install'

/** Non-blocking install card: native prompt on Chromium, manual steps on iOS. */
export function InstallHint() {
  const { t } = useTranslation()
  const [hidden, setHidden] = useState(() => !shouldOfferInstall())
  const prompt = useSyncExternalStore(subscribeInstallPrompt, getInstallPrompt)
  const ios = isIos()

  if (hidden || (!prompt && !ios)) return null

  const dismiss = () => {
    dismissInstallHint()
    setHidden(true)
  }

  return (
    <aside className="card install-hint" aria-labelledby="install-hint-title">
      <h2 id="install-hint-title" className="card__title">
        {t('install.title')}
      </h2>
      <p>{prompt ? t('install.body') : t('install.ios')}</p>
      <div className="card__actions">
        {prompt && (
          <button type="button" className="button button--primary" onClick={() => void promptInstall().then(dismiss)}>
            {t('install.action')}
          </button>
        )}
        <button type="button" className="button" onClick={dismiss}>
          {t('install.later')}
        </button>
      </div>
    </aside>
  )
}
