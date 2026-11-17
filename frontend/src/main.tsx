import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './i18n'
import './index.css'
import { requestPersistentStorage } from './offline/db'
import { syncEngine } from './offline/sync'
import { listenForInstallPrompt, recordVisit } from './pwa/install'

recordVisit()
listenForInstallPrompt()
syncEngine.start()
void requestPersistentStorage()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
