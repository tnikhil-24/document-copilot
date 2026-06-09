import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'

import { Sidebar } from '@/components/Sidebar'
import { api, type ThreadSummary } from '@/lib/api'
import { ThreadsContext } from '@/lib/threads-context'

export function AppShell() {
  const [threads, setThreads] = useState<ThreadSummary[]>([])

  useEffect(() => {
    api.getThreads().then(setThreads).catch(() => undefined)
  }, [])

  function prependThread(thread: ThreadSummary) {
    setThreads((prev) => [thread, ...prev.filter((t) => t.id !== thread.id)])
  }

  return (
    <ThreadsContext.Provider value={{ threads, prependThread }}>
      <div className="flex h-svh w-full overflow-hidden">
        <Sidebar />
        <main className="min-w-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </ThreadsContext.Provider>
  )
}
