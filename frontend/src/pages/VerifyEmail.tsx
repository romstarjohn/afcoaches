import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { authApi } from '../api/auth'
import { ApiError, NetworkError } from '../api/client'
import { useAuth } from '../auth/context'

type Status = 'verifying' | 'verified' | 'invalid' | 'offline' | 'error'

/** Target of the link in the verification email. */
export function VerifyEmail() {
  const { t } = useTranslation()
  const { refresh } = useAuth()
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState<Status>(token ? 'verifying' : 'invalid')

  // One request per link: the token is single-use, so a repeated call (re-render, StrictMode) must not happen.
  const sentFor = useRef<string | null>(null)
  useEffect(() => {
    if (!token || sentFor.current === token) return
    sentFor.current = token
    authApi
      .verifyEmail(token)
      .then(async () => {
        setStatus('verified')
        await refresh()
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 400) setStatus('invalid')
        else setStatus(error instanceof NetworkError ? 'offline' : 'error')
      })
  }, [token, refresh])

  return (
    <section>
      <h1>{t('auth.verify.title')}</h1>
      <p role="status">{t(`auth.verify.${status}`)}</p>
      <Link to="/" className="button button--primary button--link">
        {t('nav.home')}
      </Link>
    </section>
  )
}
