import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { authApi } from '../api/auth'
import { errorCode, fieldErrors, generalErrorKey } from '../auth/errors'
import { Field, PasswordField } from '../components/Field'
import { SubPage } from '../components/SubPage'

/** The address only changes once the link sent to the NEW address is opened. */
export function ChangeEmail() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [general, setGeneral] = useState<string | null>(null)
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setErrors({})
    setGeneral(null)
    try {
      await authApi.requestEmailChange({ new_email: email.trim(), current_password: password })
      setSentTo(email.trim())
      setPassword('')
    } catch (e) {
      const fields = fieldErrors(e)
      if (fields.new_email) setErrors({ email: t('auth.errors.emailInvalid') })
      else if (errorCode(e) === 'invalid_password') setErrors({ password: t('account.password.invalidPassword') })
      else setGeneral(generalErrorKey(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <SubPage title={t('account.email.title')}>
      {sentTo ? (
        <p role="status">{t('account.email.sent', { email: sentTo })}</p>
      ) : (
        <form className="form" onSubmit={(e) => void onSubmit(e)} noValidate>
          <Field
            id="new-email"
            label={t('account.email.newEmail')}
            type="email"
            inputMode="email"
            autoComplete="email"
            autoCapitalize="none"
            required
            value={email}
            error={errors.email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <PasswordField
            id="email-password"
            label={t('account.password.current')}
            autoComplete="current-password"
            required
            value={password}
            error={errors.password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="form__error" role="alert">
            {general ? t(general) : ''}
          </p>
          <button type="submit" className="button button--primary form__submit" disabled={busy || !email || !password}>
            {t('account.email.submit')}
          </button>
        </form>
      )}
    </SubPage>
  )
}
