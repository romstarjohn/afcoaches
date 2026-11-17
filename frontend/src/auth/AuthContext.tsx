import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Outlet } from 'react-router'
import { authApi, cacheUser, cachedUser, type AccountUser } from '../api/auth'
import { NetworkError } from '../api/client'
import i18n, { LANGUAGES, type Language } from '../i18n'
import { AuthContext, type AuthValue } from './context'

function isLanguage(value: string): value is Language {
  return (LANGUAGES as readonly string[]).includes(value)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{ status: 'loading' | 'ready'; user: AccountUser | null }>(() => ({
    status: 'loading',
    user: cachedUser(),
  }))

  const apply = useCallback((user: AccountUser | null) => {
    cacheUser(user)
    setState({ status: 'ready', user })
    // The account's language wins after sign-in and at startup.
    if (user && isLanguage(user.language) && user.language !== i18n.resolvedLanguage) {
      void i18n.changeLanguage(user.language)
    }
  }, [])

  useEffect(() => {
    let alive = true
    authApi
      .me()
      .then((user) => alive && apply(user))
      .catch((error: unknown) => {
        if (!alive) return
        // Offline: keep the cached profile. Any other answer (e.g. 403) means not signed in.
        if (error instanceof NetworkError) setState((s) => ({ ...s, status: 'ready' }))
        else apply(null)
      })
    return () => {
      alive = false
    }
  }, [apply])

  const refresh = useCallback(async () => {
    try {
      apply(await authApi.me())
    } catch {
      // offline or signed out: keep what we have
    }
  }, [apply])

  const value = useMemo<AuthValue>(
    () => ({
      status: state.status,
      user: state.user,
      login: async (email, password) => apply(await authApi.login(email, password)),
      logout: async () => {
        try {
          await authApi.logout()
        } catch {
          // offline or session already gone: the device is signed out either way
        }
        apply(null)
      },
      refresh,
      updateProfile: async (patch) => apply(await authApi.updateProfile(patch)),
      changeLanguage: async (lang) => {
        await i18n.changeLanguage(lang)
        if (!state.user) return
        try {
          apply(await authApi.updateProfile({ language: lang }))
        } catch {
          // saved on this device only for now; the account value is refreshed on the next start
        }
      },
    }),
    [state, apply, refresh],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}

/** Route element that provides the auth state to everything below it. */
export function AuthRoot() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  )
}
