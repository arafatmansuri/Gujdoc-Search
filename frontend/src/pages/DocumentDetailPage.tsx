import { ArrowLeft, CheckCircle2, ChevronLeft, ChevronRight, Download, FileText, History, Save, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, getApiError, type DocumentRecord, type DocumentRegion } from '../api'
import { invalidateMetrics, removeDocument, useAppDispatch } from '../store'

export function DocumentDetailPage() {
  const dispatch = useAppDispatch()
  const { id } = useParams()
  const documentId = Number(id)
  const [documentRecord, setDocumentRecord] = useState<DocumentRecord | null>(null)
  const [regions, setRegions] = useState<DocumentRegion[]>([])
  const [audit, setAudit] = useState<Array<{ id: number; action: string; details: Record<string, unknown>; created_at: string; user_email: string }>>([])
  const [pdfUrl, setPdfUrl] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')
  const [error, setError] = useState('')
  const [page, setPage] = useState('1')
  const [expectedText, setExpectedText] = useState('')
  const [message, setMessage] = useState('')
  const [previewPage, setPreviewPage] = useState(1)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!Number.isInteger(documentId)) return
    void Promise.all([api.getDocument(documentId), api.getRegions(documentId), api.getAudit(documentId)])
      .then(([doc, regionResponse, auditResponse]) => {
        setDocumentRecord(doc); setRegions(regionResponse.regions); setAudit(auditResponse.events)
        if (doc.has_searchable_pdf) return api.downloadSearchablePdf(documentId).then((blob) => setPdfUrl(URL.createObjectURL(blob)))
      })
      .catch((reason) => setError(getApiError(reason, 'Could not load this document.')))
    return () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl) }
  }, [documentId])

  useEffect(() => {
    if (documentRecord?.page_count) {
      setPreviewPage((current) => Math.min(current, documentRecord.page_count ?? current))
    }
  }, [documentRecord?.page_count])

  useEffect(() => {
    if (!Number.isInteger(documentId)) return
    void api.previewPage(documentId, previewPage)
      .then((blob) => setPreviewUrl(URL.createObjectURL(blob)))
      .catch(() => setPreviewUrl(''))
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }
  }, [documentId, previewPage])

  async function saveEvaluation() {
    if (!expectedText.trim()) return
    await api.addEvaluationCase(documentId, { page_number: Number(page), expected_text: expectedText })
    setExpectedText(''); setMessage('Evaluation case saved.')
  }

  async function downloadPdf() {
    if (!documentRecord) return
    const blob = await api.downloadSearchablePdf(documentId)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = documentRecord.filename
    anchor.click()
    URL.revokeObjectURL(url)
  }

  async function deleteDocument() {
    if (!window.confirm(`Delete "${documentRecord?.filename}"? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await api.deleteDocument(documentId)
      dispatch(removeDocument(documentId))
      dispatch(invalidateMetrics())
      window.location.href = '/'
    } catch (reason) {
      setError(getApiError(reason, 'Could not delete this document.'))
      setDeleting(false)
    }
  }

  if (error) return <div className="space-y-4"><Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500"><ArrowLeft size={16} />Back</Link><p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</p></div>
  if (!documentRecord) return <p className="text-sm text-slate-500">Loading document…</p>
  const layoutAnnotations = (documentRecord.layout_features?.annotations ?? []).filter((annotation) => !annotation.page_number || annotation.page_number === previewPage)
  return <div className="space-y-6">
    <Link to="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-[#e88d35]"><ArrowLeft size={16} />Back to documents</Link>
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-bold uppercase tracking-wider text-[#e88d35]">DOCUMENT REVIEW</p><h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-[#17233b]"><FileText size={22} />{documentRecord.filename}</h1><p className="mt-1 text-xs text-slate-500">{documentRecord.subject || 'No subject extracted'} · {documentRecord.metadata_status}</p></div><div className="flex flex-wrap gap-2">{documentRecord.has_searchable_pdf && <button onClick={() => void downloadPdf()} className="flex items-center gap-2 rounded-lg bg-[#17233b] px-3 py-2 text-xs font-bold text-white"><Download size={14} />Download PDF</button>}<button disabled={deleting} onClick={() => void deleteDocument()} className="flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-600 hover:bg-red-50 disabled:opacity-50"><Trash2 size={14} />{deleting ? 'Deleting…' : 'Delete document'}</button></div></div>
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,1fr)]">
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500"><span>Source overlay</span><div className="flex items-center gap-2"><button type="button" aria-label="Previous page" disabled={previewPage <= 1} onClick={() => setPreviewPage((current) => Math.max(1, current - 1))} className="grid h-8 w-8 place-items-center rounded border border-slate-200 text-slate-600 hover:border-[#e88d35] hover:text-[#e88d35] disabled:cursor-not-allowed disabled:opacity-40"><ChevronLeft size={16} /></button><label className="flex items-center gap-1 text-[10px] font-semibold normal-case tracking-normal text-slate-500">Page<input aria-label="Preview page" type="number" min="1" max={documentRecord.page_count} value={previewPage} onChange={(event) => setPreviewPage(Math.min(documentRecord.page_count ?? Number.MAX_SAFE_INTEGER, Math.max(1, Number(event.target.value) || 1)))} className="h-8 w-14 rounded border border-slate-200 px-2 text-center text-xs font-normal text-slate-700" /></label><span className="text-[10px] font-normal normal-case tracking-normal text-slate-400">of {documentRecord.page_count ?? '—'}</span><button type="button" aria-label="Next page" disabled={Boolean(documentRecord.page_count && previewPage >= documentRecord.page_count)} onClick={() => setPreviewPage((current) => Math.min(documentRecord.page_count ?? current + 1, current + 1))} className="grid h-8 w-8 place-items-center rounded border border-slate-200 text-slate-600 hover:border-[#e88d35] hover:text-[#e88d35] disabled:cursor-not-allowed disabled:opacity-40"><ChevronRight size={16} /></button></div></div>{previewUrl ? <div className="relative mx-auto max-w-2xl"><img src={previewUrl} alt={`Document page ${previewPage}`} className="block w-full" /><svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox={`0 0 ${Math.max(...regions.filter((region) => region.page_number === previewPage).map((region) => region.x1), 612)} ${Math.max(...regions.filter((region) => region.page_number === previewPage).map((region) => region.y1), 792)}`} preserveAspectRatio="none">{regions.filter((region) => region.page_number === previewPage).map((region) => <rect key={region.id} x={region.x0} y={region.y0} width={region.x1 - region.x0} height={region.y1 - region.y0} fill="none" stroke={(region.confidence ?? 0) < 0.65 ? '#dc2626' : '#2b8a83'} strokeWidth="2" />)}{layoutAnnotations.map((annotation, index) => <rect key={`layout-${index}`} x={annotation.x0} y={annotation.y0} width={annotation.x1 - annotation.x0} height={annotation.y1 - annotation.y0} fill="none" stroke={annotation.type === 'table' ? '#2563eb' : '#9333ea'} strokeDasharray="5 3" strokeWidth="3" />)}</svg></div> : <div className="grid h-64 place-items-center text-sm text-slate-400">{pdfUrl ? 'Page preview unavailable.' : 'Searchable PDF is not ready.'}</div>}</section>
      <div className="space-y-5">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-bold text-slate-700"><CheckCircle2 size={16} className="text-[#2b8a83]" />Source regions</h2><p className="mt-1 text-xs text-slate-400">Coordinates link extracted text back to the source page.</p><div className="mt-3 max-h-64 space-y-2 overflow-auto">{regions.map((region) => <div key={region.id} className="rounded border border-slate-100 p-2 text-xs"><div className="flex justify-between text-[10px] text-slate-400"><span>Page {region.page_number}</span><span>{region.confidence == null ? '—' : `${Math.round(region.confidence * 100)}%`}</span></div><p className="mt-1 text-slate-600">{region.text}</p><p className="mt-1 font-mono text-[9px] text-slate-400">({region.x0.toFixed(0)}, {region.y0.toFixed(0)})–({region.x1.toFixed(0)}, {region.y1.toFixed(0)})</p></div>)}</div></section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-bold text-slate-700"><Save size={16} />Evaluation ground truth</h2><p className="mt-1 text-xs text-slate-400">Add verified page text to measure CER.</p><input value={page} onChange={(event) => setPage(event.target.value)} type="number" min="1" className="mt-3 w-full rounded border border-slate-200 px-2 py-1.5 text-xs" placeholder="Page number" /><textarea value={expectedText} onChange={(event) => setExpectedText(event.target.value)} className="mt-2 h-20 w-full rounded border border-slate-200 px-2 py-1.5 text-xs" placeholder="Verified page text" /><button onClick={() => void saveEvaluation()} className="mt-2 rounded-lg bg-[#e88d35] px-3 py-2 text-xs font-bold text-white">Save ground truth</button>{message && <p className="mt-2 text-xs text-teal-700">{message}</p>}</section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-bold text-slate-700"><History size={16} />Audit history</h2><div className="mt-3 space-y-2">{audit.length ? audit.map((event) => <div key={event.id} className="border-l-2 border-slate-200 pl-2 text-xs"><p className="font-medium text-slate-600">{event.action}</p><p className="text-[10px] text-slate-400">{event.user_email} · {new Date(event.created_at).toLocaleString('en-IN')}</p></div>) : <p className="text-xs text-slate-400">No corrections recorded.</p>}</div></section>
      </div>
    </div>
  </div>
}
