import { useParams } from 'react-router-dom'

export function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>()

  return (
    <div className="mx-auto flex min-h-svh max-w-xl flex-col items-center justify-center gap-2 p-6 text-center">
      <h1 className="text-xl font-semibold text-foreground">Thread {threadId}</h1>
      <p className="text-sm text-muted-foreground">Chat plumbing lands in a later slice.</p>
    </div>
  )
}
