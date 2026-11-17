import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context'
import { fieldErrors, generalErrorKey } from '../auth/errors'
import { Field } from '../components/Field'
import { SubPage } from '../components/SubPage'

export function ChangeName() {
  const { t } = useTranslation()
  const { user, updateProfile } = useAuth()
  const [name, setName] = useState(user?.display_name ?? '')
  const [error, setError] = useState<string | undefined>()
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSaved(false)
    if (!name.trim()) return setError(t('auth.errors.nameRequired'))
    setBusy(true)
    setError(undefined)
    try {
      await updateProfile({ display_name: name.trim() })
      setSaved(true)
    } catch (e) {
      setError(fieldErrors(e).display_name ?? t(generalErrorKey(e)))
    } finally {
      setBusy(false)
    }
  }

  return (
    <SubPage title={t('account.name.title')}>
      <form className="form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <Field
          id="profile-name"
          label={t('auth.fields.name')}
          autoComplete="name"
          maxLength={80}
          required
          value={name}
          error={error}
          onChange={(e) => setName(e.target.value)}
        />
        <p className="form__status" role="status">
          {saved ? t('account.saved') : ''}
        </p>
        <button type="submit" className="button button--primary form__submit" disabled={busy}>
          {t('account.save')}
        </button>
      </form>
    </SubPage>
  )
}
