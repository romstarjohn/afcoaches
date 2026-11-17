import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import { routes } from './routes'
import i18n from './i18n'

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({ needRefresh: [false, vi.fn()], offlineReady: [false, vi.fn()], updateServiceWorker: vi.fn() }),
}))

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

describe('App shell', () => {
  it('renders in English by default (no saved or browser preference)', async () => {
    localStorage.clear()
    await act(() => i18n.changeLanguage('en'))
    renderAt('/')
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
  })

  it('offers a bottom navigation with the main sections', async () => {
    await act(() => i18n.changeLanguage('en'))
    renderAt('/')
    const nav = screen.getByRole('navigation', { name: 'Main menu' })
    expect(within(nav).getAllByRole('link').map((l) => l.textContent)).toEqual(['Home', 'Coaches', 'Settings'])
    expect(within(nav).getByRole('link', { name: 'Home' })).toHaveAttribute('aria-current', 'page')
    await userEvent.click(within(nav).getByRole('link', { name: 'Coaches' }))
    expect(screen.getByRole('heading', { name: 'Coaches' })).toBeInTheDocument()
  })

  it('lets the user change the language in the settings and remembers it', async () => {
    await act(() => i18n.changeLanguage('en'))
    renderAt('/settings')
    expect(screen.getByRole('radio', { name: 'English' })).toBeChecked()

    await userEvent.click(screen.getByRole('radio', { name: 'Français' }))
    expect(screen.getByRole('heading', { name: 'Réglages' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'Français' })).toBeChecked()
    expect(document.documentElement.lang).toBe('fr')
    expect(localStorage.getItem('csm.lang')).toBe('fr')
  })

  it('shows the offline notice when there is no connection', async () => {
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    await act(() => i18n.changeLanguage('en'))
    renderAt('/')
    expect(screen.getByRole('status')).toHaveTextContent('Offline – your data is saved on this device')
  })

  it('renders a not-found page for unknown routes', async () => {
    await act(() => i18n.changeLanguage('en'))
    renderAt('/does/not/exist')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
