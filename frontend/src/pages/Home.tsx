import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useAuth } from '../auth/context'
import { InstallHint } from '../components/InstallHint'

export function Home() {
  const { t } = useTranslation()
  const { user, status } = useAuth()
  return (
    <section>
      <h1>{t('home.title')}</h1>
      <p className="lead">{t('app.tagline')}</p>
      <p>{t('home.intro')}</p>
      {!user && status === 'ready' && (
        <div className="card__actions">
          <Link to="/register" className="button button--primary button--link">
            {t('auth.register.title')}
          </Link>
          <Link to="/login" className="button button--link">
            {t('auth.login.submit')}
          </Link>
        </div>
      )}
      <InstallHint />
    </section>
  )
}
