import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '@/lib/auth'

/** Redirects to `/login` when there is no session — covers missing, expired,
 * and invalid sessions alike, since Supabase clears the session in all three cases. */
export function ProtectedRoute() {
  const { session, isLoading } = useAuth()

  if (isLoading) return null

  if (session === null) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
