import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { authApi } from '../api/auth'
import { ApiError } from '../api/client'
import { fieldErrors, generalErrorKey } from '../auth/errors'
import { PasswordField } from '../components/Field'

/** Target of the link in the password reset email. */
export function ResetPassword() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const uid = params.get('uid')
  const token = params.get('token')
  const [password, setPassword] = useState('')
  const [fieldError, setFieldError] = useState<string | undefined>()
  const [general, setGeneral] = useState<string | null>(null)
  const [state, setState] = useState<'form' | 'done' | 'invalid'>(uid && token ? 'form' : 'invalid')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setFieldError(undefined)
    setGeneral(null)
    try {
      await authApi.confirmPasswordReset({ uid: uid!, token: token!, password })
      setState('done')
    } catch (error) {
      const found = fieldErrors(error)
      if (found.password) setFieldError(found.password)
      else if (error instanceof ApiError && error.status === 400) setState('invalid')
      else setGeneral(generalErrorKey(error))
    } finally {
      setBusy(false)
    }
  }

  if (state === 'done') {
    return (
      <section>
        <h1>{t('auth.reset.title')}</h1>
        <p role="status">{t('auth.reset.done')}</p>
        <Link to="/login" className="button button--primary button--link">
          {t('auth.login.submit')}
        </Link>
      </section>
    )
  }
  if (state === 'invalid') {
    return (
      <section>
        <h1>{t('auth.reset.title')}</h1>
        <p role="alert">{t('auth.reset.invalid')}</p>
        <Link to="/forgot-password" className="button button--primary button--link">
          {t('auth.forgot.submit')}
        </Link>
      </section>
    )
  }
  return (
    <section>
      <h1>{t('auth.reset.title')}</h1>
      <form className="form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <PasswordField
          id="reset-password"
          label={t('auth.fields.newPassword')}
          autoComplete="new-password"
          required
          hint={t('auth.fields.passwordHint', { count: 10 })}
          value={password}
          error={fieldError}
          onChange={(e) => setPassword(e.target.value)}
        />
        <p className="form__error" role="alert">
          {general ? t(general) : ''}
        </p>
        <button type="submit" className="button button--primary form__submit" disabled={busy || !password}>
          {t('auth.reset.submit')}
        </button>
      </form>
    </section>
  )
}
