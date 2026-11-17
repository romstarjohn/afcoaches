import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate } from 'react-router'
import { authApi } from '../api/auth'
import { useAuth } from '../auth/context'
import { fieldErrors, generalErrorKey } from '../auth/errors'
import { Field, PasswordField } from '../components/Field'
import { LANGUAGES, type Language } from '../i18n'

const MIN_PASSWORD = 10
const TOTAL_STEPS = 2 // + the signed-in start screen = 3 steps from the follower's point of view

/** Registration in two short screens; ends signed in (or on "check your inbox" for an existing email). */
export function Register() {
  const { t, i18n } = useTranslation()
  const { user, login, changeLanguage } = useAuth()
  const navigate = useNavigate()
  const heading = useRef<HTMLHeadingElement>(null)
  const [step, setStep] = useState<1 | 2>(1)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [general, setGeneral] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [checkInbox, setCheckInbox] = useState(false)
  const language = (i18n.resolvedLanguage ?? 'en') as Language

  useEffect(() => heading.current?.focus(), [step, checkInbox])

  if (user) return <Navigate to="/" replace />

  function next(event: FormEvent) {
    event.preventDefault()
    const found: Record<string, string> = {}
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) found.email = t('auth.errors.emailInvalid')
    if (password.length < MIN_PASSWORD) found.password = t('auth.errors.passwordShort', { count: MIN_PASSWORD })
    setErrors(found)
    if (Object.keys(found).length === 0) setStep(2)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return setErrors({ display_name: t('auth.errors.nameRequired') })
    setBusy(true)
    setErrors({})
    setGeneral(null)
    try {
      await authApi.register({ email: email.trim(), password, display_name: name.trim(), language })
    } catch (error) {
      const found = fieldErrors(error)
      setErrors(found)
      if (Object.keys(found).length === 0) setGeneral(generalErrorKey(error))
      else if (found.email || found.password) setStep(1)
      setBusy(false)
      return
    }
    // The account exists but is unverified: signing in right away gets the follower into the app.
    // If the email was already registered the password will not match, so we point to the inbox.
    try {
      await login(email.trim(), password)
      void navigate('/', { replace: true })
    } catch {
      setCheckInbox(true)
    } finally {
      setBusy(false)
    }
  }

  if (checkInbox) {
    return (
      <section>
        <h1 ref={heading} tabIndex={-1}>
          {t('auth.checkInbox.title')}
        </h1>
        <p>{t('auth.checkInbox.body', { email: email.trim() })}</p>
        <Link to="/login" className="button button--primary button--link">
          {t('auth.login.submit')}
        </Link>
      </section>
    )
  }

  return (
    <section>
      <h1 ref={heading} tabIndex={-1}>
        {t('auth.register.title')}
      </h1>
      <p className="form__progress">{t('auth.register.step', { current: step, total: TOTAL_STEPS })}</p>

      {step === 1 ? (
        <form className="form" onSubmit={next} noValidate>
          <Field
            id="reg-email"
            label={t('auth.fields.email')}
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
            id="reg-password"
            label={t('auth.fields.password')}
            autoComplete="new-password"
            required
            hint={t('auth.fields.passwordHint', { count: MIN_PASSWORD })}
            value={password}
            error={errors.password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit" className="button button--primary form__submit">
            {t('auth.register.next')}
          </button>
        </form>
      ) : (
        <form className="form" onSubmit={(e) => void submit(e)} noValidate>
          <Field
            id="reg-name"
            label={t('auth.fields.name')}
            autoComplete="name"
            maxLength={80}
            required
            value={name}
            error={errors.display_name}
            onChange={(e) => setName(e.target.value)}
          />
          <fieldset className="setting setting--plain">
            <legend className="setting__title">{t('settings.languageTitle')}</legend>
            <div className="choice-list">
              {LANGUAGES.map((lang) => (
                <label key={lang} className="choice">
                  <input
                    type="radio"
                    name="language"
                    value={lang}
                    checked={language === lang}
                    onChange={() => void changeLanguage(lang)}
                  />
                  <span>{t(`lang.${lang}`)}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <p className="form__error" role="alert">
            {general ? t(general) : ''}
          </p>
          <div className="form__actions">
            <button type="button" className="button" onClick={() => setStep(1)} disabled={busy}>
              {t('auth.register.back')}
            </button>
            <button type="submit" className="button button--primary" disabled={busy}>
              {t('auth.register.submit')}
            </button>
          </div>
        </form>
      )}
      <p className="form__links">
        {t('auth.register.haveAccount')} <Link to="/login">{t('auth.login.submit')}</Link>
      </p>
    </section>
  )
}
