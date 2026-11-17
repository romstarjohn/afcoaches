import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'
import { SyncStatus } from './SyncStatus'
import { TabBar } from './TabBar'
import { VerifyBanner } from './VerifyBanner'

export function Layout() {
  const { t } = useTranslation()
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          {t('app.name')}
        </Link>
      </header>
      <TabBar />
      <SyncStatus />
      <VerifyBanner />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
