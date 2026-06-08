import type { UIMessage } from 'ai'

import { cn } from '@/lib/utils'

/** Joins a message's text parts — the only part type the stub backend produces today. */
function textOf(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

export function ChatMessage({ message }: { message: UIMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[75ch] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
        )}
      >
        {textOf(message)}
      </div>
    </div>
  )
}
