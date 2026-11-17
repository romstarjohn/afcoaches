import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { bodyOf, calls, handlers, json, resetApiMock, USER } from '../test/apiMock'
import { routes } from '../routes'

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({ needRefresh: [false, vi.fn()], offlineReady: [false, vi.fn()], updateServiceWorker: vi.fn() }),
}))

beforeEach(resetApiMock)

afterEach(() => vi.unstubAllGlobals())

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

async function fillAndSubmit(email = 'ada@example.invalid', password = 'a-long-test-password') {
  await userEvent.type(screen.getByLabelText('Email address'), email)
  await userEvent.type(screen.getByLabelText('Password'), password)
  await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
}

describe('auth', () => {
  it('shows a login link in the settings when signed out', async () => {
    renderAt('/settings')
    expect(await screen.findByText('You are not logged in.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
  })

  it('logs in, applies the account language and shows the account', async () => {
    handlers['POST /api/v1/auth/login'] = () => json(200, USER)
    renderAt('/login')
    await screen.findByRole('heading', { name: 'Log in' })
    await fillAndSubmit()

    expect(await screen.findByRole('heading', { name: 'Bienvenue' })).toBeInTheDocument() // home, in French
    expect(document.documentElement.lang).toBe('fr')
    expect(bodyOf('POST /api/v1/auth/login')).toEqual({
      email: 'ada@example.invalid',
      password: 'a-long-test-password',
    })
    expect(JSON.parse(localStorage.getItem('csm.user') ?? '{}').email).toBe('ada@example.invalid')
  })

  it('refreshes the CSRF token after login so the next unsafe request works', async () => {
    handlers['POST /api/v1/auth/login'] = () => json(200, USER)
    handlers['POST /api/v1/auth/logout'] = () => new Response(null, { status: 204 })
    renderAt('/login')
    await screen.findByRole('heading', { name: 'Log in' })
    await fillAndSubmit()
    await screen.findByRole('heading', { name: 'Bienvenue' })
    await userEvent.click(screen.getByRole('link', { name: 'Réglages' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Se déconnecter' }))
    await waitFor(() => expect(calls('POST /api/v1/auth/logout')).toHaveLength(1))
    // one CSRF fetch before login, a second one before logout
    expect(calls('GET /api/v1/auth/csrf')).toHaveLength(2)
  })

  it('shows one generic error for wrong credentials and keeps the entered values', async () => {
    handlers['POST /api/v1/auth/login'] = () => json(400, { code: 'invalid_credentials' })
    renderAt('/login')
    await screen.findByRole('heading', { name: 'Log in' })
    await fillAndSubmit('ada@example.invalid', 'wrong-password-123')
    expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.')
    expect(screen.getByLabelText('Email address')).toHaveValue('ada@example.invalid')
    expect(screen.getByLabelText('Password')).toHaveValue('wrong-password-123')
  })

  it('tells the user when the account is temporarily locked', async () => {
    handlers['POST /api/v1/auth/login'] = () => json(429, { code: 'too_many_attempts' })
    renderAt('/login')
    await screen.findByRole('heading', { name: 'Log in' })
    await fillAndSubmit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts')
  })

  it('explains that logging in needs a connection when offline', async () => {
    handlers['POST /api/v1/auth/login'] = () => {
      throw new TypeError('Failed to fetch')
    }
    renderAt('/login')
    await screen.findByRole('heading', { name: 'Log in' })
    await fillAndSubmit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Logging in needs an internet connection')
  })

  it('keeps the signed-in user when the app starts offline', async () => {
    localStorage.setItem('csm.user', JSON.stringify(USER))
    handlers['GET /api/v1/auth/me'] = () => {
      throw new TypeError('Failed to fetch')
    }
    renderAt('/settings')
    expect(await screen.findByText('ada@example.invalid')).toBeInTheDocument()
    expect(localStorage.getItem('csm.user')).not.toBeNull()
  })

  it('forgets the cached user when the server says the session is gone', async () => {
    localStorage.setItem('csm.user', JSON.stringify(USER))
    renderAt('/settings') // default handler: me -> 403
    expect(await screen.findByText('You are not logged in.')).toBeInTheDocument()
    expect(localStorage.getItem('csm.user')).toBeNull()
  })

  it('redirects away from the login page when already signed in', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en' })
    renderAt('/login')
    expect(await screen.findByRole('heading', { name: 'Welcome' })).toBeInTheDocument()
  })

  it('saves the language on the account when signed in', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en' })
    handlers['PATCH /api/v1/auth/me'] = () => json(200, { ...USER, language: 'fr' })
    renderAt('/settings')
    await screen.findByText(/Signed in as/)
    await userEvent.click(screen.getByRole('radio', { name: 'Français' }))
    await waitFor(() => expect(calls('PATCH /api/v1/auth/me')).toHaveLength(1))
    expect(bodyOf('PATCH /api/v1/auth/me')).toEqual({ language: 'fr' })
    expect(screen.getByRole('heading', { name: 'Réglages' })).toBeInTheDocument()
  })

  it('does not call the API for the language when signed out', async () => {
    renderAt('/settings')
    await screen.findByText('You are not logged in.')
    await userEvent.click(screen.getByRole('radio', { name: 'Français' }))
    expect(screen.getByRole('heading', { name: 'Réglages' })).toBeInTheDocument()
    expect(calls('PATCH /api/v1/auth/me')).toHaveLength(0)
  })

  it('signs out locally even when offline', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en' })
    handlers['POST /api/v1/auth/logout'] = () => {
      throw new TypeError('Failed to fetch')
    }
    renderAt('/settings')
    await userEvent.click(await screen.findByRole('button', { name: 'Log out' }))
    expect(await screen.findByText('You are not logged in.')).toBeInTheDocument()
    expect(localStorage.getItem('csm.user')).toBeNull()
  })
})
