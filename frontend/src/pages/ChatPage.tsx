import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { Chat } from '@/components/chat/Chat'
import { Button } from '@/components/ui/button'
import { api, ApiError, type ChatThread } from '@/lib/api'
import { supabase } from '@/lib/supabase'

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>()
  const [thread, setThread] = useState<ChatThread | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    api
      .get<ChatThread>('/thread')
      .then((loaded) => {
        if (!cancelled) setThread(loaded)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        console.error('Failed to load thread history:', cause)
        setError(cause instanceof ApiError ? cause.message : 'Something went wrong.')
      })

    return () => {
      cancelled = true
    }
    // `GET /thread` always returns the analyst's single thread (Slice 1),
    // so this only needs to run once per mount, not per `threadId`.
  }, [])

  if (error) {
    return (
      <div className="mx-auto flex min-h-svh max-w-xl flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" onClick={() => void supabase.auth.signOut()}>
          Log out
        </Button>
      </div>
    )
  }

  if (thread === null || threadId === undefined) {
    return (
      <div className="flex min-h-svh items-center justify-center p-6">
        <p className="text-sm text-muted-foreground">Loading your conversation…</p>
      </div>
    )
  }

  return <Chat threadId={threadId} initialMessages={thread.messages} />
}
