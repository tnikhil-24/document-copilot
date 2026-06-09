import { LogOut, SquarePen } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { useThreadsContext } from '@/lib/threads-context'
import { cn } from '@/lib/utils'

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const secs = Math.floor(diffMs / 1000)
  const mins = Math.floor(secs / 60)
  const hours = Math.floor(mins / 60)
  const days = Math.floor(hours / 24)

  if (secs < 60) return 'now'
  if (mins < 60) return `${mins}m`
  if (hours < 24) return `${hours}h`
  if (days === 1) return 'yday'
  if (days < 7) return `${days}d`
  return new Date(iso).toLocaleDateString('en', { month: 'short', day: 'numeric' })
}

export function Sidebar() {
  const { threadId } = useParams<{ threadId: string }>()
  const navigate = useNavigate()
  const { threads } = useThreadsContext()

  return (
    <aside className="flex h-svh w-[260px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Header */}
      <div className="flex flex-col gap-3 px-3 py-4">
        <span className="px-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-foreground/40">
          Document Copilot
        </span>
        <button
          onClick={() => navigate('/')}
          className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-[13px] font-medium text-sidebar-foreground/70 ring-1 ring-sidebar-border transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
        >
          <SquarePen className="size-3.5 shrink-0" />
          New chat
        </button>
      </div>

      {/* Thread list */}
      <div className="border-t border-sidebar-border" />
      <nav className="flex-1 overflow-y-auto px-2 py-2">
        {threads.length === 0 ? (
          <p className="px-2 py-3 text-[11px] text-sidebar-foreground/30">
            No conversations yet
          </p>
        ) : (
          <ul className="flex flex-col gap-px">
            {threads.map((thread) => {
              const isActive = thread.id === threadId
              return (
                <li key={thread.id}>
                  <button
                    onClick={() => navigate(`/chat/${thread.id}`)}
                    className={cn(
                      'flex w-full items-center gap-2 border-l-2 py-2 pl-2 pr-2.5 text-left transition-colors',
                      isActive
                        ? 'border-primary bg-sidebar-accent text-sidebar-accent-foreground'
                        : 'border-transparent text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground'
                    )}
                  >
                    <span className="flex-1 truncate text-[12.5px] font-medium leading-snug">
                      {thread.title ?? 'New conversation'}
                    </span>
                    <span className="shrink-0 font-mono text-[10px] tabular-nums opacity-50">
                      {formatRelativeTime(thread.updated_at)}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          onClick={() => void supabase.auth.signOut()}
        >
          <LogOut className="size-3.5" />
          <span className="text-xs">Log out</span>
        </Button>
      </div>
    </aside>
  )
}
