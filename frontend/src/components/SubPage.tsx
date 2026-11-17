import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

/** A settings sub-screen: an installed PWA has no browser back button, so it brings its own. */
export function SubPage({ title, children }: { title: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <section>
      <Link to="/settings" className="back-link">
        {t('account.back')}
      </Link>
      <h1>{title}</h1>
      {children}
    </section>
  )
}
