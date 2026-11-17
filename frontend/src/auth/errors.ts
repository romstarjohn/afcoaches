import { ApiError, NetworkError, RateLimitedError } from '../api/client'

/** Field errors from a DRF 400: { password: ["..."], email: ["..."] } (messages are already localized). */
export function fieldErrors(error: unknown): Record<string, string> {
  const out: Record<string, string> = {}
  if (error instanceof ApiError && error.status === 400 && error.detail && typeof error.detail === 'object') {
    for (const [field, value] of Object.entries(error.detail)) {
      if (Array.isArray(value) && typeof value[0] === 'string') out[field] = value.join(' ')
    }
  }
  return out
}

/** Translation key for failures that are not field errors. */
export function generalErrorKey(error: unknown): string {
  if (errorCode(error) === 'too_many_attempts') return 'auth.errors.tooManyAttempts'
  if (error instanceof RateLimitedError) return 'auth.errors.tooManyRequests'
  if (error instanceof NetworkError) return 'auth.errors.network'
  return 'auth.errors.generic'
}

/** The machine-readable `code` of a 400/429 answer, e.g. "invalid_password". */
export function errorCode(error: unknown): string | undefined {
  const detail = error instanceof ApiError || error instanceof RateLimitedError ? error.detail : undefined
  return detail && typeof detail === 'object' && 'code' in detail ? String(detail.code) : undefined
}
