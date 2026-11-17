import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context'
import { AccountCard } from '../components/AccountCard'
import { LANGUAGES, type Language } from '../i18n'

export function Settings() {
  const { t, i18n } = useTranslation()
  const { changeLanguage } = useAuth()
  return (
    <section>
      <h1>{t('settings.title')}</h1>
      <AccountCard />
      <fieldset className="setting">
        <legend className="setting__title">{t('settings.languageTitle')}</legend>
        <p className="setting__help">{t('settings.languageHelp')}</p>
        <div className="choice-list">
          {LANGUAGES.map((lang: Language) => (
            <label key={lang} className="choice">
              <input
                type="radio"
                name="language"
                value={lang}
                checked={i18n.resolvedLanguage === lang}
                onChange={() => void changeLanguage(lang)}
              />
              <span>{t(`lang.${lang}`)}</span>
            </label>
          ))}
        </div>
      </fieldset>
    </section>
  )
}
