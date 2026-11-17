import { useState, type InputHTMLAttributes } from 'react'
import { useTranslation } from 'react-i18next'

interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'className'> {
  id: string
  label: string
  hint?: string
  /** Already translated message. */
  error?: string
}

/** Label + input + optional hint and error, wired for screen readers. */
export function Field({ id, label, hint, error, ...input }: FieldProps) {
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="field__input" aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...input} />
      {hint && (
        <p id={`${id}-hint`} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

/** Password field with a "show password" toggle (typing on a phone is error-prone). */
export function PasswordField({ type: _ignored, ...props }: FieldProps) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(false)
  return (
    <div>
      <Field {...props} type={visible ? 'text' : 'password'} autoCapitalize="none" autoCorrect="off" spellCheck={false} />
      <label className="choice choice--inline">
        <input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} />
        <span>{t('auth.fields.showPassword')}</span>
      </label>
    </div>
  )
}
