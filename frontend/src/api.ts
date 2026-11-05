import axios from 'axios'

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type DocumentRecord = {
  id: number
  filename: string
  status: DocumentStatus
  created_at?: string
  file_size?: number
  page_count?: number
  has_searchable_pdf?: boolean
  document_number?: string | null
  document_date?: string | null
  subject?: string | null
  issuing_office?: string | null
  referenced_documents?: string[]
  metadata_confidence?: number | null
  metadata_status?: 'unavailable' | 'needs_review' | 'verified'
  ocr_confidence?: number | null
  uncertain_regions?: number
  layout_features?: {
    tables?: number
    stamp_like_regions?: number
    annotations?: Array<{ type: 'table' | 'stamp'; page_number?: number; x0: number; y0: number; x1: number; y1: number }>
  }
  processing_started_at?: string | null
  processing_completed_at?: string | null
  processing_error?: string | null
}

export type DocumentRegion = {
  id: number
  page_number: number
  text: string
  x0: number
  y0: number
  x1: number
  y1: number
  confidence: number | null
}

export type SearchResult = {
  chunk_id: number
  document_id: number
  filename: string
  content: string
  page_number: number
  distance?: number
  region?: { x0: number; y0: number; x1: number; y1: number } | null
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
    return data as { id: number; email: string; role: 'reviewer' | 'admin' }
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
  async metrics() {
    const { data } = await client.get('/documents/metrics/summary')
    return data as {
      completed_documents: number
      failed_documents: number
      verified_metadata_documents: number
      average_ocr_confidence: number
      uncertain_regions: number
      average_processing_seconds: number
    }
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
  async correctMetadata(id: number, metadata: {
    document_number: string | null
    document_date: string | null
    subject: string | null
    issuing_office: string | null
    referenced_documents: string[]
  }) {
    const { data } = await client.patch(`/documents/${id}/metadata`, metadata)
    return data as { document_id: number; metadata_status: string; message: string }
  },
  async search(query: string, limit = 8) {
    const { data } = await client.post('/documents/search', { query, limit })
    return data as { query: string; total_results: number; results: SearchResult[] }
  },
  async searchRecords(filters: {
    query: string
    document_number: string
    issuing_office: string
    date_from: string
    date_to: string
  }) {
    const { data } = await client.post('/documents/records/search', filters)
    return data as { items: DocumentRecord[]; total: number; limit: number; offset: number }
  },
  async getRegions(id: number, pageNumber?: number) {
    const { data } = await client.get(`/documents/${id}/regions`, {
      params: pageNumber ? { page_number: pageNumber } : undefined,
    })
    return data as { document_id: number; regions: DocumentRegion[] }
  },
  async previewPage(id: number, pageNumber: number) {
    const { data } = await client.get(`/documents/${id}/preview`, {
      params: { page_number: pageNumber },
      responseType: 'blob',
    })
    return data as Blob
  },
  async listUsers() {
    const { data } = await client.get('/admin/users')
    return data as Array<{ id: number; email: string; role: 'reviewer' | 'admin'; is_active: boolean; created_at: string }>
  },
  async updateUserRole(id: number, role: 'reviewer' | 'admin') {
    const { data } = await client.patch(`/admin/users/${id}/role`, { role })
    return data as { id: number; email: string; role: 'reviewer' | 'admin' }
  },
  async getAudit(id: number) {
    const { data } = await client.get(`/documents/${id}/audit`)
    return data as { document_id: number; events: Array<{ id: number; action: string; details: Record<string, unknown>; created_at: string; user_email: string }> }
  },
  async addEvaluationCase(id: number, payload: {
    page_number: number
    expected_text: string
    expected_document_number?: string
    expected_date?: string
    expected_subject?: string
    expected_issuing_office?: string
    expected_region?: { x0: number; y0: number; x1: number; y1: number }
  }) {
    const { data } = await client.post(`/documents/${id}/evaluation`, payload)
    return data as { id: number; document_id: number; page_number: number }
  },
  async evaluationMetrics() {
    const { data } = await client.get('/documents/evaluation/metrics')
    return data as { evaluation_cases: number; ocr_character_error_rate: number | null; metadata_precision_recall: number | null; source_region_accuracy: number | null; search_evaluation_cases: number; search_success_rate: number | null }
  },
  async addSearchEvaluationCase(query: string, expectedDocumentIds: number[]) {
    const { data } = await client.post('/documents/evaluation/search-case', {
      query,
      expected_document_ids: expectedDocumentIds,
    })
    return data as { id: number; query: string; expected_document_ids: number[] }
  },
  async runSearchEvaluation(caseId: number) {
    const { data } = await client.post('/documents/evaluation/search-run', { case_id: caseId })
    return data as { case_id: number; success: boolean; result_count: number }
  },
  async correctRegion(id: number, text: string) {
    const { data } = await client.patch(`/documents/regions/${id}`, { text })
    return data as { region_id: number; text: string; confidence: number }
  },
  async downloadSearchablePdf(id: number) {
    const { data } = await client.get(`/documents/${id}/searchable-pdf`, {
      responseType: 'blob',
    })
    return data as Blob
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
