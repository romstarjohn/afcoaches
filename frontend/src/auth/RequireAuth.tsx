import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './context'

/** Route wrapper for screens that need a signed-in member. Signed-out visitors go to the login page. */
export function RequireAuth() {
  const { user, status } = useAuth()
  const location = useLocation()
  if (user) return <Outlet />
  if (status === 'loading') return null
  return <Navigate to="/login" replace state={{ from: location.pathname }} />
}
