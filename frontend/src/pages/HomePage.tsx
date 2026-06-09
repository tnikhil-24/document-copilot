import { ArrowUp, LoaderCircle } from 'lucide-react'
import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import { useThreadsContext } from '@/lib/threads-context'

const SUGGESTIONS = [
  'Netflix content costs in 2023?',
  'Tesla capex trends 2021–2025?',
  'JPMorgan CET1 ratio 2024?',
  'Costco membership revenue growth?',
]

function makeTitle(text: string): string {
  const t = text.trim()
  if (t.length <= 60) return t
  const cut = t.slice(0, 60)
  const lastSpace = cut.lastIndexOf(' ')
  return lastSpace > 0 ? cut.slice(0, lastSpace) : cut
}

export function HomePage() {
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const { prependThread } = useThreadsContext()

  async function submit() {
    const text = input.trim()
    if (!text || isSubmitting) return
    setError(null)
    setIsSubmitting(true)

    try {
      const thread = await api.createThread()
      prependThread({ ...thread, title: makeTitle(text) })
      navigate(`/chat/${thread.id}`, { state: { pendingMessage: text } })
    } catch (cause: unknown) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'Failed to start conversation. Please try again.'
      )
      setIsSubmitting(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <div className="flex h-full flex-col items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl space-y-8">
        {/* Heading */}
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/50">
            Document Copilot
          </p>
          <h1 className="text-[28px] font-semibold leading-tight tracking-tight text-foreground">
            Research the filings.
          </h1>
          <p className="text-sm text-muted-foreground">
            Ask about earnings, costs, and strategy across 25 SEC filings —{' '}
            Netflix, Tesla, Costco, JPMorgan, United Healthcare, 2021–2025.
          </p>
        </div>

        {/* Composer */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the filings…"
            disabled={isSubmitting}
            rows={4}
            className="resize-none text-sm"
            autoFocus
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button
            type="submit"
            className="w-full gap-2"
            disabled={isSubmitting || !input.trim()}
          >
            {isSubmitting ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Starting conversation…
              </>
            ) : (
              <>
                <ArrowUp className="size-4" />
                Ask
              </>
            )}
          </Button>
        </form>

        {/* Suggestions */}
        <div className="space-y-2">
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground/40">
            Try asking
          </p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                disabled={isSubmitting}
                onClick={() => setInput(s)}
                className="rounded-md border border-border bg-muted/40 px-3 py-1.5 text-left text-[12px] text-muted-foreground transition-colors hover:border-foreground/20 hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
