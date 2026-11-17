import type { RouteObject } from 'react-router'
import { AuthRoot } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { Layout } from './components/Layout'
import { ChangeEmail } from './pages/ChangeEmail'
import { ChangeName } from './pages/ChangeName'
import { ChangePassword } from './pages/ChangePassword'
import { Coaches } from './pages/Coaches'
import { ConfirmEmailChange } from './pages/ConfirmEmailChange'
import { ForgotPassword } from './pages/ForgotPassword'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { NotFound } from './pages/NotFound'
import { Register } from './pages/Register'
import { ResetPassword } from './pages/ResetPassword'
import { Settings } from './pages/Settings'
import { VerifyEmail } from './pages/VerifyEmail'

export const routes: RouteObject[] = [
  {
    element: <AuthRoot />,
    children: [
      {
        element: <Layout />,
        children: [
        { index: true, element: <Home /> },
          { path: 'coaches', element: <Coaches /> },
          { path: 'settings', element: <Settings /> },
          {
            element: <RequireAuth />,
            children: [
              { path: 'settings/name', element: <ChangeName /> },
              { path: 'settings/email', element: <ChangeEmail /> },
              { path: 'settings/password', element: <ChangePassword /> },
            ],
          },
          { path: 'confirm-email-change', element: <ConfirmEmailChange /> },
          { path: 'login', element: <Login /> },
          { path: 'register', element: <Register /> },
          { path: 'verify-email', element: <VerifyEmail /> },
          { path: 'forgot-password', element: <ForgotPassword /> },
          { path: 'reset-password', element: <ResetPassword /> },
          { path: '*', element: <NotFound /> },
        ],
      },
    ],
  },
]
