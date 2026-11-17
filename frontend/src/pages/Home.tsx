import { useTranslation } from 'react-i18next'
import { InstallHint } from '../components/InstallHint'

export function Home() {
  const { t } = useTranslation()
  return (
    <section>
      <h1>{t('home.title')}</h1>
      <p className="lead">{t('app.tagline')}</p>
      <p>{t('home.intro')}</p>
      <InstallHint />
    </section>
  )
}
