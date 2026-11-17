import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { authApi } from '../api/auth'
import { generalErrorKey } from '../auth/errors'
import { Field } from '../components/Field'

export function ForgotPassword() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await authApi.requestPasswordReset(email.trim())
      setSent(true) // same message whether or not the account exists
    } catch (e) {
      setError(generalErrorKey(e))
    } finally {
      setBusy(false)
    }
  }

  if (sent) {
    return (
      <section>
        <h1>{t('auth.forgot.title')}</h1>
        <p role="status">{t('auth.forgot.sent')}</p>
        <Link to="/login">{t('auth.login.submit')}</Link>
      </section>
    )
  }
  return (
    <section>
      <h1>{t('auth.forgot.title')}</h1>
      <p>{t('auth.forgot.intro')}</p>
      <form className="form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <Field
          id="forgot-email"
          label={t('auth.fields.email')}
          type="email"
          inputMode="email"
          autoComplete="email"
          autoCapitalize="none"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <p className="form__error" role="alert">
          {error ? t(error) : ''}
        </p>
        <button type="submit" className="button button--primary form__submit" disabled={busy || !email}>
          {t('auth.forgot.submit')}
        </button>
      </form>
    </section>
  )
}
