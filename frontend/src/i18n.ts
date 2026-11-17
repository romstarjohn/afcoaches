import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { setApiLanguage } from './api/client'
import en from './locales/en.json'
import fr from './locales/fr.json'

export const LANGUAGES = ['fr', 'en'] as const
export type Language = (typeof LANGUAGES)[number]
const STORAGE_KEY = 'csm.lang'

function initialLanguage(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'fr' || saved === 'en') return saved
  } catch {
    // storage unavailable (private mode): fall through
  }
  return navigator.language?.toLowerCase().startsWith('en') ? 'en' : 'fr'
}

function apply(lang: string) {
  document.documentElement.lang = lang
  setApiLanguage(lang)
}

void i18n.use(initReactI18next).init({
  resources: { fr: { translation: fr }, en: { translation: en } },
  lng: initialLanguage(),
  fallbackLng: 'fr',
  interpolation: { escapeValue: false }, // React escapes already
})
apply(i18n.language)

i18n.on('languageChanged', (lang) => {
  apply(lang)
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // ignore: preference is a convenience only
  }
})

export default i18n
