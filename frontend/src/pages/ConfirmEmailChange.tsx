import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { authApi } from '../api/auth'
import { ApiError, NetworkError } from '../api/client'
import { useAuth } from '../auth/context'

type Status = 'confirming' | 'done' | 'invalid' | 'offline' | 'error'

/** Target of the link in the "confirm your new email address" message. Works signed out. */
export function ConfirmEmailChange() {
  const { t } = useTranslation()
  const { refresh } = useAuth()
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState<Status>(token ? 'confirming' : 'invalid')

  // One request per link: the token is single-use, so a repeated call (re-render, StrictMode) must not happen.
  const sentFor = useRef<string | null>(null)
  useEffect(() => {
    if (!token || sentFor.current === token) return
    sentFor.current = token
    authApi
      .confirmEmailChange(token)
      .then(async () => {
        setStatus('done')
        await refresh()
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 400) setStatus('invalid')
        else setStatus(error instanceof NetworkError ? 'offline' : 'error')
      })
  }, [token, refresh])

  return (
    <section>
      <h1>{t('account.confirmEmail.title')}</h1>
      <p role="status">{t(`account.confirmEmail.${status}`)}</p>
      <Link to="/" className="button button--primary button--link">
        {t('nav.home')}
      </Link>
    </section>
  )
}
