/**
 * Same-origin API client: session cookie + CSRF header. No tokens in localStorage.
 */

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, detail: unknown) {
    super(`API error ${status}`)
    this.status = status
    this.detail = detail
  }
}

/** Not logged in (DRF session auth answers 403 without credentials). */
export class AuthRequiredError extends ApiError {}

/** No network / server unreachable: the caller should keep data locally and retry later. */
export class NetworkError extends Error {}

let csrfToken: string | null = null
let language = 'fr'

export function setApiLanguage(lang: string) {
  language = lang
}

export function resetCsrfToken() {
  csrfToken = null
}

async function fetchCsrfToken(): Promise<string> {
  const body = await request<{ csrfToken: string }>('GET', '/api/v1/auth/csrf')
  csrfToken = body.csrfToken
  return csrfToken
}

const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function isCsrfFailure(detail: unknown) {
  const text = typeof detail === 'object' && detail && 'detail' in detail ? String(detail.detail) : ''
  return text.startsWith('CSRF Failed')
}

export async function request<T>(method: string, url: string, body?: unknown, retried = false): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json', 'Accept-Language': language }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (UNSAFE.has(method)) headers['X-CSRFToken'] = csrfToken ?? (await fetchCsrfToken())

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    throw new NetworkError(error instanceof Error ? error.message : 'network error')
  }

  const contentType = response.headers.get('Content-Type') ?? ''
  const data: unknown = contentType.includes('application/json') ? await response.json() : null

  if (response.ok) return data as T
  if (response.status === 403 && UNSAFE.has(method) && !retried && isCsrfFailure(data)) {
    resetCsrfToken() // token rotated (e.g. after login): fetch a fresh one and retry once
    return request<T>(method, url, body, true)
  }
  if (response.status === 401 || response.status === 403) {
    if (!isCsrfFailure(data)) throw new AuthRequiredError(response.status, data)
  }
  if (response.status >= 500 || response.status === 429) throw new NetworkError(`server ${response.status}`)
  throw new ApiError(response.status, data)
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body: unknown) => request<T>('POST', url, body),
}
