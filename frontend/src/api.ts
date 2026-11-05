import axios from 'axios'

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type DocumentRecord = {
  id: number
  filename: string
  status: DocumentStatus
  created_at?: string
  file_size?: number
  page_count?: number
}

export type SearchResult = {
  chunk_id: number
  document_id: number
  filename: string
  content: string
  page_number: number
  distance?: number
}

export type AskResponse = {
  question: string
  answer: string
  sources: Array<{
    source_number: number
    document_id: number
    filename: string
    page_number: number
    chunk_id: number
  }>
}

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('gujdoc_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const api = {
  async login(email: string, password: string) {
    const body = new URLSearchParams({ username: email, password })
    const { data } = await client.post('/auth/login', body, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data as { access_token: string; refresh_token: string; token_type: string }
  },
  async register(email: string, password: string) {
    const { data } = await client.post('/auth/register', { email, password })
    return data as { id: number; email: string; message: string }
  },
  async me() {
    const { data } = await client.get('/auth/me')
    return data as { id: number; email: string }
  },
  async logout(refreshToken: string) {
    await client.post('/auth/logout', { refresh_token: refreshToken })
  },
  async changePassword(currentPassword: string, newPassword: string) {
    const { data } = await client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return data as { message: string }
  },
  async listDocuments() {
    const { data } = await client.get('/documents')
    const items = Array.isArray(data) ? data : data?.items
    if (!Array.isArray(items)) {
      throw new Error('Invalid documents response from the API')
    }
    return items as DocumentRecord[]
  },
  async upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await client.post('/documents/upload', form)
    return data as { document_id: number; filename: string; status: DocumentStatus }
  },
  async deleteDocument(id: number) {
    await client.delete(`/documents/${id}`)
  },
  async retryDocument(id: number) {
    const { data } = await client.post(`/documents/${id}/retry`)
    return data as { status: string }
  },
  async getDocument(id: number) {
    const { data } = await client.get(`/documents/${id}`)
    return data as DocumentRecord
  },
  async search(query: string, limit = 8) {
    const { data } = await client.post('/documents/search', { query, limit })
    return data as { query: string; total_results: number; results: SearchResult[] }
  },
  async ask(question: string, documentId?: number) {
    const path = documentId ? `/documents/ask/${documentId}` : '/documents/ask'
    const { data } = await client.post(path, { question, limit: 5 })
    return data as AskResponse
  },
}

export function getApiError(error: unknown, fallback = 'Something went wrong. Please try again.') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}
