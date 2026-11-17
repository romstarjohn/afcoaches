import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError, NetworkError, RateLimitedError } from '../api/client'
import { useAuth } from '../auth/context'

function errorKey(error: unknown): string {
  if (error instanceof RateLimitedError) return 'auth.errors.tooManyAttempts'
  if (error instanceof NetworkError) return 'auth.errors.network'
  if (error instanceof ApiError && error.status === 400) return 'auth.errors.invalidCredentials'
  return 'auth.errors.generic'
}

export function Login() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to={from} replace />

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
      void navigate(from, { replace: true })
    } catch (e) {
      setError(errorKey(e)) // entered values stay in place
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h1>{t('auth.login.title')}</h1>
      <form className="form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <div className="field">
          <label htmlFor="login-email">{t('auth.fields.email')}</label>
          <input
            id="login-email"
            className="field__input"
            type="email"
            inputMode="email"
            autoComplete="email"
            autoCapitalize="none"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="login-password">{t('auth.fields.password')}</label>
          <input
            id="login-password"
            className="field__input"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <p className="form__error" role="alert">
          {error ? t(error) : ''}
        </p>
        <button type="submit" className="button button--primary form__submit" disabled={busy || !email || !password}>
          {t('auth.login.submit')}
        </button>
      </form>
      <p className="form__links">
        <Link to="/forgot-password">{t('auth.login.forgot')}</Link>
      </p>
      <p className="form__links">
        {t('auth.login.noAccount')} <Link to="/register">{t('auth.register.title')}</Link>
      </p>
    </section>
  )
}
