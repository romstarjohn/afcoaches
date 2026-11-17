import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { authApi } from '../api/auth'
import { useAuth } from '../auth/context'
import { errorCode, fieldErrors, generalErrorKey } from '../auth/errors'
import { Field, PasswordField } from '../components/Field'
import { SubPage } from '../components/SubPage'

type Phase = 'current' | 'code' | 'done'

/** Changing the password needs the current password first, then a code sent to the account's email. */
export function ChangePassword() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [phase, setPhase] = useState<Phase>('current')
  const [current, setCurrent] = useState('')
  const [code, setCode] = useState('')
  const [next, setNext] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [general, setGeneral] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<void>, onError: (e: unknown) => void) {
    setBusy(true)
    setErrors({})
    setGeneral(null)
    try {
      await action()
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  const requestCode = (event: FormEvent) => {
    event.preventDefault()
    return run(
      async () => {
        await authApi.requestPasswordChange(current)
        setPhase('code')
      },
      (e) => {
        if (errorCode(e) === 'invalid_password') setErrors({ current: t('account.password.invalidPassword') })
        else setGeneral(generalErrorKey(e))
      },
    )
  }

  const confirm = (event: FormEvent) => {
    event.preventDefault()
    return run(
      async () => {
        await authApi.confirmPasswordChange({ code: code.trim(), new_password: next })
        setCurrent('')
        setCode('')
        setNext('')
        setPhase('done')
      },
      (e) => {
        const fields = fieldErrors(e)
        if (fields.new_password) setErrors({ next: fields.new_password })
        else if (errorCode(e) === 'invalid_or_expired_code') setErrors({ code: t('account.password.invalidCode') })
        else setGeneral(generalErrorKey(e))
      },
    )
  }

  return (
    <SubPage title={t('account.password.title')}>
      {phase === 'current' && (
        <form className="form" onSubmit={(e) => void requestCode(e)} noValidate>
          <p>{t('account.password.intro')}</p>
          <PasswordField
            id="pw-current"
            label={t('account.password.current')}
            autoComplete="current-password"
            required
            value={current}
            error={errors.current}
            onChange={(e) => setCurrent(e.target.value)}
          />
          <p className="form__error" role="alert">
            {general ? t(general) : ''}
          </p>
          <button type="submit" className="button button--primary form__submit" disabled={busy || !current}>
            {t('account.password.sendCode')}
          </button>
        </form>
      )}

      {phase === 'code' && (
        <form className="form" onSubmit={(e) => void confirm(e)} noValidate>
          <p>{t('account.password.codeSent', { email: user?.email ?? '' })}</p>
          <Field
            id="pw-code"
            label={t('account.password.code')}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            required
            value={code}
            error={errors.code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
          <PasswordField
            id="pw-new"
            label={t('auth.fields.newPassword')}
            autoComplete="new-password"
            required
            hint={t('auth.fields.passwordHint', { count: 10 })}
            value={next}
            error={errors.next}
            onChange={(e) => setNext(e.target.value)}
          />
          <p className="form__error" role="alert">
            {general ? t(general) : ''}
          </p>
          <div className="form__actions">
            <button type="button" className="button" disabled={busy} onClick={() => setPhase('current')}>
              {t('account.password.newCode')}
            </button>
            <button type="submit" className="button button--primary" disabled={busy || code.length < 6 || !next}>
              {t('account.password.submit')}
            </button>
          </div>
        </form>
      )}

      {phase === 'done' && <p role="status">{t('account.password.done')}</p>}
    </SubPage>
  )
}
