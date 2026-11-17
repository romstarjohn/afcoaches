import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'
import { CoachesIcon, HomeIcon, SettingsIcon } from './Icons'

const TABS = [
  { to: '/', key: 'home', Icon: HomeIcon, end: true },
  { to: '/coaches', key: 'coaches', Icon: CoachesIcon, end: false },
  { to: '/settings', key: 'settings', Icon: SettingsIcon, end: false },
] as const

/** Primary navigation: bottom tab bar on phones (thumb zone), top bar on wide screens. */
export function TabBar() {
  const { t } = useTranslation()
  return (
    <nav className="tabbar" aria-label={t('nav.label')}>
      {TABS.map(({ to, key, Icon, end }) => (
        <NavLink key={key} to={to} end={end} className="tab">
          <Icon />
          <span className="tab__label">{t(`nav.${key}`)}</span>
        </NavLink>
      ))}
    </nav>
  )
}
