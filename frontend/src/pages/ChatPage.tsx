import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { Chat } from '@/components/chat/Chat'
import { api, ApiError, type ThreadDetail } from '@/lib/api'

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const [thread, setThread] = useState<ThreadDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  // Captured once at mount via initializer — survives the router-state-clearing
  // re-render that happens before Chat mounts (while getThread is loading).
  const [pendingMessage] = useState(
    () => (location.state as { pendingMessage?: string } | null)?.pendingMessage
  )

  // Clear router state so a page refresh does not re-submit.
  useEffect(() => {
    if (pendingMessage) {
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [pendingMessage, navigate, location.pathname])

  useEffect(() => {
    if (!threadId) return
    let cancelled = false

    api
      .getThread(threadId)
      .then((loaded) => {
        if (!cancelled) setThread(loaded)
      })
      .catch((cause: unknown) => {
        if (cancelled) return
        console.error('Failed to load thread:', cause)
        if (cause instanceof ApiError && cause.status === 404) {
          setNotFound(true)
        } else {
          setError(cause instanceof ApiError ? cause.message : 'Something went wrong.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [threadId])

  if (notFound) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-sm text-muted-foreground">Conversation not found.</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  if (thread === null || threadId === undefined) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-sm text-muted-foreground">Loading conversation…</p>
      </div>
    )
  }

  return (
    <Chat threadId={threadId} initialMessages={thread.messages} pendingMessage={pendingMessage} />
  )
}
