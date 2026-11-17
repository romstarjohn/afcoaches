import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '../routes'
import { bodyOf, calls, handlers, json, resetApiMock, USER } from '../test/apiMock'

vi.mock('virtual:pwa-register/react', () => ({
  useRegisterSW: () => ({ needRefresh: [false, vi.fn()], offlineReady: [false, vi.fn()], updateServiceWorker: vi.fn() }),
}))

beforeEach(resetApiMock)
afterEach(() => vi.unstubAllGlobals())

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />)
}

const PASSWORD = 'a-long-test-password'
const accepted = () => json(202, { status: 'pending_verification' })

async function step1(email = 'ada@example.invalid', password = PASSWORD) {
  await userEvent.type(await screen.findByLabelText('Email address'), email)
  await userEvent.type(screen.getByLabelText('Password'), password)
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
}

describe('registration', () => {
  it('registers in two short screens and ends signed in on the start screen', async () => {
    handlers['POST /api/v1/auth/register'] = accepted
    handlers['POST /api/v1/auth/login'] = () => json(200, { ...USER, language: 'en' })
    renderAt('/register')

    expect(await screen.findByText('Step 1 of 2')).toBeInTheDocument()
    await step1()
    expect(screen.getByText('Step 2 of 2')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Your name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Welcome' })).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/register')).toEqual({
      email: 'ada@example.invalid',
      password: PASSWORD,
      display_name: 'Ada',
      language: 'en',
    })
    expect(bodyOf('POST /api/v1/auth/login')).toEqual({ email: 'ada@example.invalid', password: PASSWORD })
  })

  it('sends the language picked in step 2 and switches the UI at once', async () => {
    handlers['POST /api/v1/auth/register'] = accepted
    renderAt('/register')
    await step1()
    await userEvent.click(screen.getByRole('radio', { name: 'Français' }))
    expect(await screen.findByLabelText('Votre nom')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Votre nom'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }))
    await waitFor(() => expect(calls('POST /api/v1/auth/register')).toHaveLength(1))
    expect(bodyOf('POST /api/v1/auth/register').language).toBe('fr')
  })

  it('validates step 1 locally and does not advance', async () => {
    renderAt('/register')
    await step1('not-an-email', 'short')
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Use at least 10 characters.')).toBeInTheDocument()
    expect(screen.getByText('Step 1 of 2')).toBeInTheDocument()
  })

  it('shows the generic inbox screen when the email already has an account', async () => {
    handlers['POST /api/v1/auth/register'] = accepted
    handlers['POST /api/v1/auth/login'] = () => json(400, { code: 'invalid_credentials' })
    renderAt('/register')
    await step1()
    await userEvent.type(screen.getByLabelText('Your name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('heading', { name: 'Check your inbox' })).toBeInTheDocument()
    expect(screen.getByText(/ada@example.invalid/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
  })

  it('returns to step 1 with the server message when the password is refused', async () => {
    handlers['POST /api/v1/auth/register'] = () => json(400, { password: ['This password is too common.'] })
    renderAt('/register')
    await step1()
    await userEvent.type(screen.getByLabelText('Your name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('This password is too common.')).toBeInTheDocument()
    expect(screen.getByLabelText('Email address')).toHaveValue('ada@example.invalid')
    expect(screen.getByLabelText('Password')).toHaveValue(PASSWORD)
  })

  it('keeps the entered data when the connection is missing', async () => {
    renderAt('/register') // register is unmocked: behaves like offline
    await step1()
    await userEvent.type(screen.getByLabelText('Your name'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No connection')
    expect(screen.getByLabelText('Your name')).toHaveValue('Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByLabelText('Email address')).toHaveValue('ada@example.invalid')
  })

  it('can show the password', async () => {
    renderAt('/register')
    const field = await screen.findByLabelText('Password')
    expect(field).toHaveAttribute('type', 'password')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Show password' }))
    expect(field).toHaveAttribute('type', 'text')
  })
})

describe('entry points', () => {
  it('offers registration and login on the start screen when signed out', async () => {
    renderAt('/')
    expect(await screen.findByRole('link', { name: 'Create account' })).toHaveAttribute('href', '/register')
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
  })

  it('links the login page to registration and password reset', async () => {
    renderAt('/login')
    expect(await screen.findByRole('link', { name: 'Forgot password?' })).toHaveAttribute('href', '/forgot-password')
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute('href', '/register')
  })
})

describe('email verification', () => {
  it('confirms the address from the link', async () => {
    handlers['POST /api/v1/auth/verify-email'] = () => json(200, { status: 'verified' })
    renderAt('/verify-email?token=abc%3Adef')
    expect(await screen.findByText('Your email address is confirmed. Thank you!')).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/verify-email')).toEqual({ token: 'abc:def' })
  })

  it('refreshes the profile so the banner disappears', async () => {
    let verified = false
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en', email_verified: verified })
    handlers['POST /api/v1/auth/verify-email'] = () => {
      verified = true
      return json(200, { status: 'verified' })
    }
    renderAt('/verify-email?token=t')
    await screen.findByText('Your email address is confirmed. Thank you!')
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Email verification' })).toBeNull())
  })

  it('explains an invalid or expired link', async () => {
    handlers['POST /api/v1/auth/verify-email'] = () => json(400, { code: 'invalid_or_expired_token' })
    renderAt('/verify-email?token=bad')
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
  })

  it('treats a link without token as invalid without calling the API', async () => {
    renderAt('/verify-email')
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
    expect(calls('POST /api/v1/auth/verify-email')).toHaveLength(0)
  })

  it('shows a banner to unverified members and can resend the email', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en' })
    handlers['POST /api/v1/auth/resend-verification'] = accepted
    renderAt('/')
    const banner = await screen.findByRole('complementary', { name: 'Email verification' })
    await userEvent.click(screen.getByRole('button', { name: 'Resend email' }))
    expect(await screen.findByText('Email sent. Check your inbox.')).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/resend-verification')).toEqual({ email: 'ada@example.invalid' })
    expect(banner).toBeInTheDocument()
  })

  it('shows no banner for verified members or visitors', async () => {
    handlers['GET /api/v1/auth/me'] = () => json(200, { ...USER, language: 'en', email_verified: true })
    renderAt('/')
    await screen.findByRole('heading', { name: 'Welcome' })
    expect(screen.queryByRole('complementary', { name: 'Email verification' })).toBeNull()
  })
})

describe('password reset', () => {
  it('shows the same confirmation after requesting a link', async () => {
    handlers['POST /api/v1/auth/password-reset'] = () => json(202, { status: 'reset_requested' })
    renderAt('/forgot-password')
    await userEvent.type(await screen.findByLabelText('Email address'), 'nobody@example.invalid')
    await userEvent.click(screen.getByRole('button', { name: 'Send link' }))
    expect(await screen.findByText(/If an account exists for this address/)).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/password-reset')).toEqual({ email: 'nobody@example.invalid' })
  })

  it('asks for a connection when offline and keeps the address', async () => {
    renderAt('/forgot-password')
    await userEvent.type(await screen.findByLabelText('Email address'), 'ada@example.invalid')
    await userEvent.click(screen.getByRole('button', { name: 'Send link' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No connection')
    expect(screen.getByLabelText('Email address')).toHaveValue('ada@example.invalid')
  })

  it('sets the new password from the link', async () => {
    handlers['POST /api/v1/auth/password-reset/confirm'] = () => json(200, { status: 'password_changed' })
    renderAt('/reset-password?uid=MQ&token=tok-123')
    await userEvent.type(await screen.findByLabelText('New password'), 'a-brand-new-password')
    await userEvent.click(screen.getByRole('button', { name: 'Save password' }))
    expect(await screen.findByText('Your password was changed. You can log in now.')).toBeInTheDocument()
    expect(bodyOf('POST /api/v1/auth/password-reset/confirm')).toEqual({
      uid: 'MQ',
      token: 'tok-123',
      password: 'a-brand-new-password',
    })
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
  })

  it('shows the server message for a weak password and keeps the form', async () => {
    handlers['POST /api/v1/auth/password-reset/confirm'] = () => json(400, { password: ['This password is too short.'] })
    renderAt('/reset-password?uid=MQ&token=t')
    await userEvent.type(await screen.findByLabelText('New password'), 'short')
    await userEvent.click(screen.getByRole('button', { name: 'Save password' }))
    expect(await screen.findByText('This password is too short.')).toBeInTheDocument()
    expect(screen.getByLabelText('New password')).toHaveValue('short')
  })

  it('offers a new link when the old one is invalid', async () => {
    handlers['POST /api/v1/auth/password-reset/confirm'] = () => json(400, { code: 'invalid_or_expired_token' })
    renderAt('/reset-password?uid=MQ&token=old')
    await userEvent.type(await screen.findByLabelText('New password'), 'a-brand-new-password')
    await userEvent.click(screen.getByRole('button', { name: 'Save password' }))
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Send link' })).toHaveAttribute('href', '/forgot-password')
  })

  it('rejects a link without uid or token right away', async () => {
    renderAt('/reset-password?uid=MQ')
    expect(await screen.findByText(/invalid or has expired/)).toBeInTheDocument()
  })
})
