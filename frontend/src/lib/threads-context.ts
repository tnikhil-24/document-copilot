import { createContext, useContext } from 'react'

import type { ThreadSummary } from '@/lib/api'

type ThreadsContextValue = {
  threads: ThreadSummary[]
  prependThread: (thread: ThreadSummary) => void
}

export const ThreadsContext = createContext<ThreadsContextValue>({
  threads: [],
  prependThread: () => undefined,
})

export const useThreadsContext = () => useContext(ThreadsContext)
