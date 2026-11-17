import { act } from '@testing-library/react'
import { vi } from 'vitest'
import { resetCsrfToken } from '../api/client'
import i18n from '../i18n'

export const USER = {
  id: 1,
  email: 'ada@example.invalid',
  display_name: 'Ada',
  language: 'fr',
  role: 'member',
  email_verified: false,
}

type Handler = (body: unknown) => Response | Promise<Response>

export const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

/** Route table for the mocked fetch: key is "METHOD /path". Reset by resetApiMock(). */
export let handlers: Record<string, Handler> = {}
export const fetchMock = vi.fn<typeof fetch>()

export function calls(key: string) {
  return fetchMock.mock.calls.filter(([url, init]) => `${init?.method ?? 'GET'} ${url}` === key)
}

export function bodyOf(key: string, index = 0) {
  return JSON.parse(String(calls(key)[index][1]?.body))
}

/** Signed-out by default; unmocked requests behave like a lost connection. English UI. */
export async function resetApiMock() {
  localStorage.clear()
  resetCsrfToken()
  handlers = {
    'GET /api/v1/auth/me': () => json(403, { detail: 'Not authenticated' }),
    'GET /api/v1/auth/csrf': () => json(200, { csrfToken: 'tok' }),
  }
  fetchMock.mockReset()
  fetchMock.mockImplementation(async (url, init) => {
    const handler = handlers[`${init?.method ?? 'GET'} ${url}`]
    if (!handler) throw new TypeError(`unmocked ${init?.method ?? 'GET'} ${url}`)
    return handler(init?.body ? JSON.parse(String(init.body)) : undefined)
  })
  vi.stubGlobal('fetch', fetchMock)
  await act(() => i18n.changeLanguage('en'))
}
