import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '../routes'
import { bodyOf, calls, handlers, json, resetApiMock, USER } from '../test/apiMock'

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({ needRefresh: [false, vi.fn()], offlineReady: [false, vi.fn()], updateServiceWorker: vi.fn() }),
}))

const ME = { ...USER, language: 'en', email_verified: true }

beforeEach(async () => {
  await resetApiMock()
  handlers['GET /api/v1/auth/me'] = () => json(200, ME)
})
afterEach(() => vi.unstubAllGlobals())

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

describe('settings navigation', () => {
  it('links the account sub-screens when signed in', async () => {
    renderAt('/settings')
    expect(await screen.findByRole('link', { name: 'Change name' })).toHaveAttribute('href', '/settings/name')
    expect(screen.getByRole('link', { name: 'Change email address' })).toHaveAttribute('href', '/settings/email')
    expect(screen.getByRole('link', { name: 'Change password' })).toHaveAttribute('href', '/settings/password')
  })

  it('has a way back to the settings on every sub-screen', async () => {
    renderAt('/settings/password')
    expect(await screen.findByRole('link', { name: 'Back to settings' })).toHaveAttribute('href', '/settings')
  })

  it('sends signed-out visitors to the login page and back afterwards', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(403, { detail: 'Not authenticated' })
    handlers['POST /api/v1/auth/login'] = () => json(200, ME)
    renderAt('/settings/password')
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Email address'), 'ada@example.invalid')
    await userEvent.type(screen.getByLabelText('Password'), 'a-long-test-password')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('heading', { name: 'Change password' })).toBeInTheDocument()
  })
})

describe('change name', () => {
  it('saves the new name', async () => {
    handlers['PATCH /api/v1/auth/me'] = () => json(200, { ...ME, display_name: 'Ada L.' })
    renderAt('/settings/name')
    const field = await screen.findByLabelText('Your name')
    expect(field).toHaveValue('Ada')
    await userEvent.clear(field)
    await userEvent.type(field, 'Ada L.')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(bodyOf('PATCH /api/v1/auth/me')).toEqual({ display_name: 'Ada L.' })
  })

  it('refuses an empty name without calling the API', async () => {
    renderAt('/settings/name')
    await userEvent.clear(await screen.findByLabelText('Your name'))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Enter your name.')).toBeInTheDocument()
    expect(calls('PATCH /api/v1/auth/me')).toHaveLength(0)
  })

  it('says so when offline and keeps the text', async () => {
    renderAt('/settings/name') // PATCH unmocked: no connection
    const field = await screen.findByLabelText('Your name')
    await userEvent.type(field, 'x')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText(/No connection/)).toBeInTheDocument()
    expect(field).toHaveValue('Adax')
  })
})

describe('change password', () => {
  async function requestCode() {
    handlers['POST /api/v1/auth/password-change/request'] = () => json(202, { status: 'code_sent' })
    await userEvent.type(await screen.findByLabelText('Current password'), 'a-long-test-password')
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
    await screen.findByLabelText('Code from the email')
  }

  it('asks for the current password, then the emailed code, then the new password', async () => {
    renderAt('/settings/password')
    await requestCode()
    expect(bodyOf('POST /api/v1/auth/password-change/request')).toEqual({ current_password: 'a-long-test-password' })
    expect(screen.getByText(/ada@example.invalid/)).toBeInTheDocument()

    handlers['POST /api/v1/auth/password-change/confirm'] = () => json(200, { status: 'password_changed' })
    await userEvent.type(screen.getByLabelText('Code from the email'), '123456')
    await userEvent.type(screen.getByLabelText('New password'), 'a-brand-new-password')
    await userEvent.click(screen.getByRole('button', { name: 'Change password' }))
    expect(await screen.findByText(/Your password was changed/)).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/password-change/confirm')).toEqual({
      code: '123456',
      new_password: 'a-brand-new-password',
    })
  })

  it('reports a wrong current password and sends no code', async () => {
    handlers['POST /api/v1/auth/password-change/request'] = () => json(400, { code: 'invalid_password' })
    renderAt('/settings/password')
    await userEvent.type(await screen.findByLabelText('Current password'), 'wrong-password-123')
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
    expect(await screen.findByText('Current password is incorrect.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Code from the email')).toBeNull()
  })

  it('tells the user when too many wrong passwords locked the account', async () => {
    handlers['POST /api/v1/auth/password-change/request'] = () => json(429, { code: 'too_many_attempts' })
    renderAt('/settings/password')
    await userEvent.type(await screen.findByLabelText('Current password'), 'x')
    await userEvent.click(screen.getByRole('button', { name: 'Send code' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts')
  })

  it('reports a wrong or expired code and keeps the form', async () => {
    renderAt('/settings/password')
    await requestCode()
    handlers['POST /api/v1/auth/password-change/confirm'] = () => json(400, { code: 'invalid_or_expired_code' })
    await userEvent.type(screen.getByLabelText('Code from the email'), '000000')
    await userEvent.type(screen.getByLabelText('New password'), 'a-brand-new-password')
    await userEvent.click(screen.getByRole('button', { name: 'Change password' }))
    expect(await screen.findByText('The code is wrong or has expired.')).toBeInTheDocument()
    expect(screen.getByLabelText('New password')).toHaveValue('a-brand-new-password')
  })

  it('shows the server message for a weak new password', async () => {
    renderAt('/settings/password')
    await requestCode()
    handlers['POST /api/v1/auth/password-change/confirm'] = () =>
      json(400, { new_password: ['This password is entirely numeric.'] })
    await userEvent.type(screen.getByLabelText('Code from the email'), '123456')
    await userEvent.type(screen.getByLabelText('New password'), '1234567890123')
    await userEvent.click(screen.getByRole('button', { name: 'Change password' }))
    expect(await screen.findByText('This password is entirely numeric.')).toBeInTheDocument()
  })

  it('accepts digits only in the code field and needs all six', async () => {
    renderAt('/settings/password')
    await requestCode()
    await userEvent.type(screen.getByLabelText('Code from the email'), '12ab34')
    expect(screen.getByLabelText('Code from the email')).toHaveValue('1234')
    await userEvent.type(screen.getByLabelText('New password'), 'a-brand-new-password')
    expect(screen.getByRole('button', { name: 'Change password' })).toBeDisabled()
  })

  it('lets the user go back to request a new code', async () => {
    renderAt('/settings/password')
    await requestCode()
    await userEvent.click(screen.getByRole('button', { name: 'Send a new code' }))
    expect(await screen.findByLabelText('Current password')).toBeInTheDocument()
  })
})

describe('change email', () => {
  it('sends the link to the new address and does not claim the change happened', async () => {
    handlers['POST /api/v1/auth/email-change/request'] = () => json(202, { status: 'confirmation_sent' })
    renderAt('/settings/email')
    await userEvent.type(await screen.findByLabelText('New email address'), 'new@example.invalid')
    await userEvent.type(screen.getByLabelText('Current password'), 'a-long-test-password')
    await userEvent.click(screen.getByRole('button', { name: 'Send confirmation link' }))
    expect(await screen.findByText(/We sent a link to new@example.invalid/)).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/email-change/request')).toEqual({
      new_email: 'new@example.invalid',
      current_password: 'a-long-test-password',
    })
  })

  it('reports a wrong current password', async () => {
    handlers['POST /api/v1/auth/email-change/request'] = () => json(400, { code: 'invalid_password' })
    renderAt('/settings/email')
    await userEvent.type(await screen.findByLabelText('New email address'), 'new@example.invalid')
    await userEvent.type(screen.getByLabelText('Current password'), 'wrong-password-123')
    await userEvent.click(screen.getByRole('button', { name: 'Send confirmation link' }))
    expect(await screen.findByText('Current password is incorrect.')).toBeInTheDocument()
    expect(screen.getByLabelText('New email address')).toHaveValue('new@example.invalid')
  })

  it('reports an invalid address', async () => {
    handlers['POST /api/v1/auth/email-change/request'] = () => json(400, { new_email: ['Enter a valid email address.'] })
    renderAt('/settings/email')
    await userEvent.type(await screen.findByLabelText('New email address'), 'nope')
    await userEvent.type(screen.getByLabelText('Current password'), 'a-long-test-password')
    await userEvent.click(screen.getByRole('button', { name: 'Send confirmation link' }))
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
  })
})

describe('confirm email change', () => {
  it('applies the change from the link, also when signed out, and refreshes the profile', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(403, { detail: 'Not authenticated' })
    handlers['POST /api/v1/auth/email-change/confirm'] = () => json(200, { status: 'email_changed' })
    renderAt('/confirm-email-change?token=abc%3Adef')
    expect(await screen.findByText(/Your email address was changed/)).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/email-change/confirm')).toEqual({ token: 'abc:def' })
    await waitFor(() => expect(calls('GET /api/v1/auth/me').length).toBeGreaterThanOrEqual(2))
  })

  it('explains an invalid link and treats a missing token without calling the API', async () => {
    handlers['POST /api/v1/auth/email-change/confirm'] = () => json(400, { code: 'invalid_or_expired_token' })
    const first = renderAt('/confirm-email-change?token=bad')
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
    first.unmount()
    renderAt('/confirm-email-change')
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
    expect(calls('POST /api/v1/auth/email-change/confirm')).toHaveLength(1)
  })
})
