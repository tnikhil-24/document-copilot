import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

const TIMEOUT_MS = 15_000

export class ApiError extends Error {
  readonly status: number | null
  readonly isNetworkError: boolean

  constructor(message: string, status: number | null, isNetworkError: boolean) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

type RequestOptions = {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

/** Thin fetch wrapper: resolves the base URL, injects the Supabase bearer token,
 * and converts both network failures and non-2xx responses into `ApiError`. */
export async function request<T>(path: string, options: RequestOptions): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS)

  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method: options.method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: controller.signal,
    })
  } catch {
    throw new ApiError('Could not reach the server', null, true)
  } finally {
    clearTimeout(timeout)
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail =
      typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : `Request failed with status ${response.status}`
    throw new ApiError(detail, response.status, false)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
