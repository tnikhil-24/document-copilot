import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'
import { ArrowUp, LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

import { ChatMessage } from '@/components/chat/ChatMessage'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

type ChatProps = {
  threadId: string
  initialMessages: UIMessage[]
  pendingMessage?: string
}

/** Wires the AI SDK's `useChat` to `/chat/stream`, injecting the Supabase
 * access token per request so a refreshed token is always used. */
export function Chat({ threadId, initialMessages, pendingMessage }: ChatProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const hasSentPendingRef = useRef(false)

  // The transport only forwards whatever chat `id` it's given via
  // `prepareSendMessagesRequest` — it doesn't need to change with `threadId`.
  const transport = useMemo(
    () =>
      new DefaultChatTransport<UIMessage>({
        api: `${env.apiBaseUrl}/chat/stream`,
        headers: async () => {
          const { data } = await supabase.auth.getSession()
          const token = data.session?.access_token
          const headers: Record<string, string> = {}
          if (token) headers.Authorization = `Bearer ${token}`
          return headers
        },
        prepareSendMessagesRequest: ({ id, messages, headers, credentials, api }) => ({
          api,
          headers,
          credentials,
          body: { threadId: id, messages },
        }),
      }),
    []
  )

  const { messages, sendMessage, status, error, clearError } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
  })

  const isBusy = status === 'submitted' || status === 'streaming'

  // Auto-submit the pending message from the home page composer, once.
  useEffect(() => {
    if (!pendingMessage || hasSentPendingRef.current) return
    hasSentPendingRef.current = true
    void sendMessage({ text: pendingMessage })
  }, [pendingMessage, sendMessage])

  useEffect(() => {
    if (error) console.error('Chat request failed:', error)
  }, [error])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  function submit() {
    const text = input.trim()
    if (!text || isBusy) return
    setInput('')
    if (error) clearError()
    void sendMessage({ text })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="mx-auto flex h-svh w-full max-w-3xl flex-col p-4">
      <header className="flex items-center justify-between border-b pb-3">
        <h1 className="text-lg font-semibold text-foreground">Document Copilot</h1>
        <Button variant="outline" size="sm" onClick={() => void supabase.auth.signOut()}>
          Log out
        </Button>
      </header>

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto py-4">
        {messages.length === 0 && (
          <p className="m-auto max-w-sm text-center text-sm text-muted-foreground">
            Ask a question about the corpus to start the conversation.
          </p>
        )}
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {status === 'submitted' && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" />
            Thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="mb-2 text-sm text-destructive">
          Something went wrong sending your message. Please try again.
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2 border-t pt-3">
        <Textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about the filings…"
          disabled={isBusy}
          rows={1}
          className="resize-none"
        />
        <Button type="submit" size="icon" disabled={isBusy || !input.trim()}>
          {isBusy ? (
            <LoaderCircle className="size-4 animate-spin" />
          ) : (
            <ArrowUp className="size-4" />
          )}
        </Button>
      </form>
    </div>
  )
}
