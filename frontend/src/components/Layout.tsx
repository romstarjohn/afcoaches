import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'
import { LANGUAGES } from '../i18n'
import { SyncStatus } from './SyncStatus'

export function Layout() {
  const { t, i18n } = useTranslation()
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          {t('app.name')}
        </Link>
        <nav className="lang-switch" aria-label={t('lang.label')}>
          {LANGUAGES.map((lang) => (
            <button
              key={lang}
              type="button"
              className="lang-switch__btn"
              aria-pressed={i18n.language === lang}
              onClick={() => void i18n.changeLanguage(lang)}
            >
              {lang.toUpperCase()}
              <span className="visually-hidden"> – {t(`lang.${lang}`)}</span>
            </button>
          ))}
        </nav>
      </header>
      <SyncStatus />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
