import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { api, ApiError } from '@/lib/api'
import { supabase } from '@/lib/supabase'

type Me = {
  id: string
  email: string
  full_name: string | null
}

export function HomePage() {
  const [me, setMe] = useState<Me | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    api
      .get<Me>('/me')
      .then((profile) => {
        if (!cancelled) setMe(profile)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        setError(cause instanceof ApiError ? cause.message : 'Something went wrong.')
      })

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mx-auto flex min-h-svh max-w-xl flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold text-foreground">Document Copilot</h1>
      {error && <p className="text-sm text-destructive">{error}</p>}
      {me && (
        <p className="text-sm text-muted-foreground">
          Signed in as {me.full_name ?? me.email}
        </p>
      )}
      <Button variant="outline" onClick={() => void supabase.auth.signOut()}>
        Log out
      </Button>
    </div>
  )
}
