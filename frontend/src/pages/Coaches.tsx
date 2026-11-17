import { useTranslation } from 'react-i18next'

/** Placeholder until coach discovery (backlog 000004). */
export function Coaches() {
  const { t } = useTranslation()
  return (
    <section>
      <h1>{t('coaches.title')}</h1>
      <p className="lead">{t('coaches.empty')}</p>
    </section>
  )
}
