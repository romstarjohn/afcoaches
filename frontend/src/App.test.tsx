import { act, render, screen } from '@testing-library/react'
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
  it('renders in French by default and switches to English', async () => {
    await act(() => i18n.changeLanguage('fr'))
    renderAt('/')
    expect(screen.getByRole('heading', { name: 'Bienvenue' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('fr')

    await userEvent.click(screen.getByRole('button', { name: /EN/ }))
    expect(screen.getByRole('heading', { name: 'Welcome' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('en')
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
