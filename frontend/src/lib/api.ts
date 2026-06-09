import type { UIMessage } from 'ai'

import { request } from '@/lib/http'

export { ApiError } from '@/lib/http'

export type ThreadSummary = { id: string; title: string | null; updated_at: string }
export type ThreadDetail = { id: string; title: string | null; messages: UIMessage[] }

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  getThreads: () => request<ThreadSummary[]>('/threads', { method: 'GET' }),
  createThread: () => request<ThreadSummary>('/threads', { method: 'POST' }),
  getThread: (id: string) => request<ThreadDetail>(`/threads/${id}`, { method: 'GET' }),
}
