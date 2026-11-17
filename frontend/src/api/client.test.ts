import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, AuthRequiredError, NetworkError, resetCsrfToken, setApiLanguage } from './client'

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  resetCsrfToken()
  setApiLanguage('fr')
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

const headersOf = (call: number) => (fetchMock.mock.calls[call][1]?.headers ?? {}) as Record<string, string>

describe('api client', () => {
  it('sends same-origin credentials and the UI language', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { id: 1 }))
    setApiLanguage('en')
    await api.get('/api/v1/auth/me')
    expect(fetchMock.mock.calls[0][1]?.credentials).toBe('same-origin')
    expect(headersOf(0)['Accept-Language']).toBe('en')
    expect(headersOf(0)['X-CSRFToken']).toBeUndefined()
  })

  it('fetches a CSRF token before the first unsafe request and reuses it', async () => {
    fetchMock
      .mockResolvedValueOnce(json(200, { csrfToken: 'tok1' }))
      .mockResolvedValueOnce(json(200, { results: [] }))
      .mockResolvedValueOnce(json(200, { results: [] }))
    await api.post('/api/v1/sync/push', { operations: [] })
    await api.post('/api/v1/sync/push', { operations: [] })
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(['/api/v1/auth/csrf', '/api/v1/sync/push', '/api/v1/sync/push'])
    expect(headersOf(1)['X-CSRFToken']).toBe('tok1')
    expect(headersOf(2)['X-CSRFToken']).toBe('tok1')
  })

  it('refreshes a rotated CSRF token once and retries', async () => {
    fetchMock
      .mockResolvedValueOnce(json(200, { csrfToken: 'old' }))
      .mockResolvedValueOnce(json(403, { detail: 'CSRF Failed: CSRF token incorrect.' }))
      .mockResolvedValueOnce(json(200, { csrfToken: 'new' }))
      .mockResolvedValueOnce(json(200, { ok: true }))
    await expect(api.post('/x', {})).resolves.toEqual({ ok: true })
    expect(headersOf(3)['X-CSRFToken']).toBe('new')
  })

  it('maps errors to typed exceptions', async () => {
    fetchMock.mockResolvedValueOnce(json(403, { detail: 'Authentication credentials were not provided.' }))
    await expect(api.get('/a')).rejects.toBeInstanceOf(AuthRequiredError)

    fetchMock.mockResolvedValueOnce(json(503, {}))
    await expect(api.get('/a')).rejects.toBeInstanceOf(NetworkError)

    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(api.get('/a')).rejects.toBeInstanceOf(NetworkError)

    fetchMock.mockResolvedValueOnce(json(400, { operations: ['invalid'] }))
    const error = await api.get('/a').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).not.toBeInstanceOf(AuthRequiredError)
  })
})
