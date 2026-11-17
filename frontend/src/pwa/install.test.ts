import { beforeEach, describe, expect, it, vi } from 'vitest'
import { dismissInstallHint, isIos, MIN_VISITS, recordVisit, shouldOfferInstall } from './install'

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('matchMedia', () => ({ matches: false }))
})

describe('install hint rules', () => {
  it('is not offered on the first visit', () => {
    recordVisit()
    expect(shouldOfferInstall()).toBe(false)
  })

  it('is offered from the second visit until dismissed, then again after 30 days', () => {
    for (let i = 0; i < MIN_VISITS; i++) recordVisit()
    const now = Date.now()
    expect(shouldOfferInstall(now)).toBe(true)
    dismissInstallHint(now)
    expect(shouldOfferInstall(now + 24 * 60 * 60_000)).toBe(false)
    expect(shouldOfferInstall(now + 31 * 24 * 60 * 60_000)).toBe(true)
  })

  it('is never offered when already installed', () => {
    for (let i = 0; i < MIN_VISITS; i++) recordVisit()
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    expect(shouldOfferInstall()).toBe(false)
  })

  it('detects iPhone and iPadOS but not desktop Mac or Android', () => {
    expect(isIos('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)', 5)).toBe(true)
    expect(isIos('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 5)).toBe(true)
    expect(isIos('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 0)).toBe(false)
    expect(isIos('Mozilla/5.0 (Linux; Android 15; Pixel 9)', 5)).toBe(false)
  })
})
