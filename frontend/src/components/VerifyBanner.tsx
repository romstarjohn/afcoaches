import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { authApi } from '../api/auth'
import { NetworkError } from '../api/client'
import { useAuth } from '../auth/context'

/** Shown to signed-in members whose email is not verified yet. They can use the app, with limits. */
export function VerifyBanner() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'offline'>('idle')
  if (!user || user.email_verified) return null

  async function resend() {
    setState('sending')
    try {
      await authApi.resendVerification(user!.email)
      setState('sent')
    } catch (error) {
      setState(error instanceof NetworkError ? 'offline' : 'idle')
    }
  }

  return (
    <aside className="verify-banner" aria-label={t('auth.banner.label')}>
      <p>{state === 'sent' ? t('auth.banner.sent') : state === 'offline' ? t('auth.errors.network') : t('auth.banner.text')}</p>
      {state !== 'sent' && (
        <button type="button" className="button" disabled={state === 'sending'} onClick={() => void resend()}>
          {t('auth.banner.resend')}
        </button>
      )}
    </aside>
  )
}
