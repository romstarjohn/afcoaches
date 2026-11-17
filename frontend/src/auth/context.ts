import { createContext, useContext } from 'react'
import type { AccountUser } from '../api/auth'
import type { Language } from '../i18n'

export interface AuthValue {
  /** 'loading' only until the first answer (or the offline fallback) is in. */
  status: 'loading' | 'ready'
  user: AccountUser | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  /** Reloads the profile from the server (e.g. after the email was verified). Offline: no-op. */
  refresh: () => Promise<void>
  /** Saves profile fields on the account. Throws on failure (network, validation). */
  updateProfile: (patch: { display_name: string }) => Promise<void>
  /** Applies the language now and saves it on the account when signed in (best effort). */
  changeLanguage: (lang: Language) => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}
