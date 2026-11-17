/**
 * Install support: Chromium fires `beforeinstallprompt`; iOS Safari has no prompt, so we show a
 * "Share → Add to Home Screen" hint instead. Never shown in standalone mode, never on the first visit,
 * and a dismissal is respected.
 */

export interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const VISITS_KEY = 'csm.visits'
const DISMISSED_KEY = 'csm.installDismissedAt'
const DISMISS_DAYS = 30
export const MIN_VISITS = 2

function storageGet(key: string) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function storageSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // storage unavailable: hint may show again, acceptable
  }
}

export function isStandalone(): boolean {
  const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true
  return iosStandalone || window.matchMedia?.('(display-mode: standalone)').matches === true
}

export function isIos(userAgent = navigator.userAgent, maxTouchPoints = navigator.maxTouchPoints): boolean {
  // iPadOS reports itself as Mac; touch support tells them apart.
  return /iPhone|iPad|iPod/.test(userAgent) || (/Macintosh/.test(userAgent) && maxTouchPoints > 1)
}

/** Call once per app start. */
export function recordVisit(): number {
  const visits = Number(storageGet(VISITS_KEY) ?? '0') + 1
  storageSet(VISITS_KEY, String(visits))
  return visits
}

export function dismissInstallHint(now = Date.now()) {
  storageSet(DISMISSED_KEY, String(now))
}

export function shouldOfferInstall(now = Date.now()): boolean {
  if (isStandalone()) return false
  if (Number(storageGet(VISITS_KEY) ?? '0') < MIN_VISITS) return false
  const dismissedAt = Number(storageGet(DISMISSED_KEY) ?? '0')
  return !dismissedAt || now - dismissedAt > DISMISS_DAYS * 24 * 60 * 60_000
}

let deferredPrompt: BeforeInstallPromptEvent | null = null
const listeners = new Set<() => void>()

export function listenForInstallPrompt() {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault() // we show our own, non-blocking UI
    deferredPrompt = event as BeforeInstallPromptEvent
    listeners.forEach((l) => l())
  })
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null
    listeners.forEach((l) => l())
  })
}

export function subscribeInstallPrompt(listener: () => void) {
  listeners.add(listener)
  return () => void listeners.delete(listener)
}

export function getInstallPrompt() {
  return deferredPrompt
}

export async function promptInstall(): Promise<boolean> {
  if (!deferredPrompt) return false
  const event = deferredPrompt
  deferredPrompt = null
  await event.prompt()
  const { outcome } = await event.userChoice
  listeners.forEach((l) => l())
  return outcome === 'accepted'
}
