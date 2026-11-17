import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useAuth } from '../auth/context'

export function AccountCard() {
  const { t } = useTranslation()
  const { user, status, logout } = useAuth()
  if (status === 'loading' && !user) return null
  return (
    <div className="setting">
      <h2 className="setting__title">{t('settings.account.title')}</h2>
      {user ? (
        <>
          <p className="setting__help">
            {t('settings.account.signedInAs')} <strong>{user.display_name || user.email}</strong>
            <br />
            <span>{user.email}</span>
          </p>
          <p className="setting__help">
            {user.email_verified ? t('settings.account.verified') : t('settings.account.notVerified')}
          </p>
          <nav className="setting__links" aria-label={t('settings.account.title')}>
            <Link to="/settings/name" className="setting__link">
              {t('account.name.title')}
            </Link>
            <Link to="/settings/email" className="setting__link">
              {t('account.email.title')}
            </Link>
            <Link to="/settings/password" className="setting__link">
              {t('account.password.title')}
            </Link>
          </nav>
          <button type="button" className="button" onClick={() => void logout()}>
            {t('settings.account.logout')}
          </button>
        </>
      ) : (
        <>
          <p className="setting__help">{t('settings.account.signedOut')}</p>
          <Link to="/login" className="button button--primary button--link">
            {t('auth.login.submit')}
          </Link>
        </>
      )}
    </div>
  )
}
