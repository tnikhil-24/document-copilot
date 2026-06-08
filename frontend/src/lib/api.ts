import type { UIMessage } from 'ai'

import { request } from '@/lib/http'

export { ApiError } from '@/lib/http'

/** The analyst's auto-created thread and its message history, as returned by `GET /thread`. */
export type ChatThread = {
  id: string
  messages: UIMessage[]
}

/** The only thing components should use to talk to the backend — handles the
 * base URL, JSON, the Supabase bearer token, timeouts, and typed `ApiError`s. */
export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
