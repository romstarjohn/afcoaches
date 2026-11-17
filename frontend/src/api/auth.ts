import { api, resetCsrfToken } from './client'

export interface AccountUser {
  id: number
  email: string
  display_name: string
  language: string
  role: string
  email_verified: boolean
}

const CACHE_KEY = 'csm.user'

/** Last known profile, so the installed app still knows who is signed in when it starts offline. */
export function cachedUser(): AccountUser | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    const user = raw ? (JSON.parse(raw) as Partial<AccountUser>) : null
    return user && typeof user.email === 'string' && typeof user.id === 'number' ? (user as AccountUser) : null
  } catch {
    return null
  }
}

export function cacheUser(user: AccountUser | null) {
  try {
    if (user) localStorage.setItem(CACHE_KEY, JSON.stringify(user))
    else localStorage.removeItem(CACHE_KEY)
  } catch {
    // storage unavailable: the app just starts without a cached profile
  }
}

export const authApi = {
  me: () => api.get<AccountUser>('/api/v1/auth/me'),
  async login(email: string, password: string) {
    const user = await api.post<AccountUser>('/api/v1/auth/login', { email, password })
    resetCsrfToken() // Django rotates the CSRF token on login
    return user
  },
  async logout() {
    try {
      await api.post('/api/v1/auth/logout', {})
    } finally {
      resetCsrfToken()
    }
  },
  register: (payload: { email: string; password: string; display_name: string; language: string }) =>
    api.post<{ status: string }>('/api/v1/auth/register', payload),
  verifyEmail: (token: string) => api.post<{ status: string }>('/api/v1/auth/verify-email', { token }),
  resendVerification: (email: string) => api.post<{ status: string }>('/api/v1/auth/resend-verification', { email }),
  requestPasswordReset: (email: string) => api.post<{ status: string }>('/api/v1/auth/password-reset', { email }),
  confirmPasswordReset: (payload: { uid: string; token: string; password: string }) =>
    api.post<{ status: string }>('/api/v1/auth/password-reset/confirm', payload),
  requestPasswordChange: (current_password: string) =>
    api.post<{ status: string }>('/api/v1/auth/password-change/request', { current_password }),
  confirmPasswordChange: (payload: { code: string; new_password: string }) =>
    api.post<{ status: string }>('/api/v1/auth/password-change/confirm', payload),
  requestEmailChange: (payload: { new_email: string; current_password: string }) =>
    api.post<{ status: string }>('/api/v1/auth/email-change/request', payload),
  confirmEmailChange: (token: string) => api.post<{ status: string }>('/api/v1/auth/email-change/confirm', { token }),
  updateProfile: (patch: Partial<Pick<AccountUser, 'display_name' | 'language'>>) =>
    api.patch<AccountUser>('/api/v1/auth/me', patch),
}
