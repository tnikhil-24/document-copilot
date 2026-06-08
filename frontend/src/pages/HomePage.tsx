import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { api, ApiError } from '@/lib/api'
import { supabase } from '@/lib/supabase'

/** Lands the analyst in their single auto-created thread — Slice 1 gives
 * every analyst exactly one conversation, so home is just a redirect. */
export function HomePage() {
  const [threadId, setThreadId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    api
      .get<{ id: string }>('/thread')
      .then((thread) => {
        if (!cancelled) setThreadId(thread.id)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        console.error('Failed to load the auto-created thread:', cause)
        setError(cause instanceof ApiError ? cause.message : 'Something went wrong.')
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (threadId !== null) {
    return <Navigate to={`/chat/${threadId}`} replace />
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-xl flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-2xl font-semibold text-foreground">Document Copilot</h1>
      {error ? (
        <>
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" onClick={() => void supabase.auth.signOut()}>
            Log out
          </Button>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Loading your conversation…</p>
      )}
    </div>
  )
}
