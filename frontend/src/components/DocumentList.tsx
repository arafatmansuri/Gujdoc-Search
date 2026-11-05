import { AlertTriangle, Check, Download, Edit3, FileText, RefreshCw, Save, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { DocumentRecord } from '../api'
import { api } from '../api'
import { StatusBadge } from './StatusBadge'
import { invalidateDocuments, useAppDispatch } from '../store'

const date = (value?: string) => value
  ? new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  : 'Just now'

type Region = { id: number; page_number: number; text: string; confidence: number | null }

export function DocumentList({ documents }: { documents: DocumentRecord[] }) {
  if (!documents.length) {
    return <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 px-5 py-14 text-center">
      <FileText className="mx-auto mb-3 text-[#e88d35]" />
      <h3 className="text-sm font-bold text-slate-700">No documents yet</h3>
      <p className="mt-1 text-xs text-slate-400">Use “Add document” in the sidebar to upload your first PDF.</p>
    </div>
  }
  return <div className="space-y-2">{documents.map((doc) => <DocumentRow key={doc.id} doc={doc} />)}</div>
}

function DocumentRow({ doc }: { doc: DocumentRecord }) {
  const dispatch = useAppDispatch()
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showUncertain, setShowUncertain] = useState(false)
  const [regions, setRegions] = useState<Region[]>([])
  const [regionDrafts, setRegionDrafts] = useState<Record<number, string>>({})
  const [loadingRegions, setLoadingRegions] = useState(false)
  const [regionError, setRegionError] = useState('')
  const [form, setForm] = useState({
    document_number: doc.document_number ?? '',
    document_date: doc.document_date ?? '',
    subject: doc.subject ?? '',
    issuing_office: doc.issuing_office ?? '',
    referenced_documents: (doc.referenced_documents ?? []).join(', '),
  })

  async function saveMetadata() {
    setSaving(true)
    try {
      await api.correctMetadata(doc.id, {
        ...form,
        document_number: form.document_number || null,
        document_date: form.document_date || null,
        subject: form.subject || null,
        issuing_office: form.issuing_office || null,
        referenced_documents: form.referenced_documents.split(',').map((value) => value.trim()).filter(Boolean),
      })
      setEditing(false)
      dispatch(invalidateDocuments())
    } finally {
      setSaving(false)
    }
  }

  async function download() {
    setDownloading(true)
    try {
      const blob = await api.downloadSearchablePdf(doc.id)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = doc.filename
      anchor.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  async function deleteDocument() {
    if (!window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await api.deleteDocument(doc.id)
      dispatch(invalidateDocuments())
    } catch {
      window.alert('Could not delete this document. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  async function loadUncertainRegions() {
    if (showUncertain) {
      setShowUncertain(false)
      return
    }
    setLoadingRegions(true)
    setRegionError('')
    try {
      const response = await api.getRegions(doc.id)
      const uncertain = response.regions.filter((region) => (region.confidence ?? 0) < 0.65)
      setRegions(uncertain)
      setRegionDrafts(Object.fromEntries(uncertain.map((region) => [region.id, region.text])))
      setShowUncertain(true)
    } catch {
      setRegionError('Could not load uncertain OCR regions.')
    } finally {
      setLoadingRegions(false)
    }
  }

  async function saveRegion(region: Region) {
    const text = regionDrafts[region.id]?.trim()
    if (!text || text === region.text) return
    await api.correctRegion(region.id, text)
    setRegions((current) => current.map((item) => item.id === region.id ? { ...item, text, confidence: 1 } : item))
    setRegionDrafts((current) => ({ ...current, [region.id]: text }))
    dispatch(invalidateDocuments())
  }

  if (editing) {
    return <div className="rounded-xl border border-orange-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between"><strong className="text-sm text-slate-700">Review metadata</strong><button onClick={() => setEditing(false)} aria-label="Cancel metadata editing"><X size={16} /></button></div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-slate-500">Document number<input value={form.document_number} onChange={(event) => setForm({ ...form, document_number: event.target.value })} className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm" /></label>
        <label className="text-xs text-slate-500">Date<input type="date" value={form.document_date} onChange={(event) => setForm({ ...form, document_date: event.target.value })} className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm" /></label>
        <label className="text-xs text-slate-500">Subject<input value={form.subject} onChange={(event) => setForm({ ...form, subject: event.target.value })} className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm" /></label>
        <label className="text-xs text-slate-500">Issuing office<input value={form.issuing_office} onChange={(event) => setForm({ ...form, issuing_office: event.target.value })} className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm" /></label>
        <label className="text-xs text-slate-500 sm:col-span-2">Referenced documents<input value={form.referenced_documents} onChange={(event) => setForm({ ...form, referenced_documents: event.target.value })} placeholder="Separate references with commas" className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm" /></label>
      </div>
      <button disabled={saving} onClick={() => void saveMetadata()} className="mt-4 flex items-center gap-2 rounded-lg bg-[#e88d35] px-3 py-2 text-xs font-bold text-white disabled:opacity-50"><Check size={14} />{saving ? 'Saving…' : 'Save as verified'}</button>
    </div>
  }

  return <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-orange-50 text-[#df7f3b]"><FileText size={19} /></div>
      <div className="min-w-0 flex-1">
        <Link to={`/documents/${doc.id}`} className="block truncate text-sm text-slate-700 hover:text-[#e88d35]">{doc.filename}</Link>
        <span className="mt-1 block text-[10px] text-slate-400">Added {date(doc.created_at)}</span>
        {(doc.subject || doc.document_number || doc.issuing_office) && <span className="mt-1 block truncate text-xs text-slate-500">{doc.subject || doc.document_number || doc.issuing_office}</span>}
        <span className={`mt-1 block text-[10px] ${doc.metadata_status === 'needs_review' ? 'text-amber-600' : 'text-slate-400'}`}>{doc.metadata_status === 'needs_review' ? 'Metadata needs review' : doc.metadata_status === 'verified' ? 'Metadata verified' : 'Metadata not detected'}</span>
        {doc.uncertain_regions ? <button onClick={() => void loadUncertainRegions()} className="mt-1 flex items-center gap-1 text-[10px] text-amber-600 hover:text-amber-800"><AlertTriangle size={11} />{loadingRegions ? 'Loading uncertain regions…' : `${doc.uncertain_regions} low-confidence OCR regions · review`}</button> : doc.ocr_confidence != null ? <span className="mt-1 block text-[10px] text-teal-700">{Math.round(doc.ocr_confidence * 100)}% OCR confidence</span> : null}
        {(doc.layout_features?.tables || doc.layout_features?.stamp_like_regions) && <span className="mt-1 block text-[10px] text-slate-500">{doc.layout_features.tables ? `${doc.layout_features.tables} table-like page(s)` : ''}{doc.layout_features.tables && doc.layout_features.stamp_like_regions ? ' · ' : ''}{doc.layout_features.stamp_like_regions ? `${doc.layout_features.stamp_like_regions} stamp-like page(s)` : ''}</span>}
        {doc.processing_error && <span className="mt-1 block text-[10px] text-red-600">Processing error: {doc.processing_error}</span>}
        {regionError && <p className="mt-1 text-[10px] text-red-600">{regionError}</p>}
      </div>
      <StatusBadge status={doc.status} />
      {doc.has_searchable_pdf && <button disabled={downloading} onClick={() => void download()} className="text-slate-400 hover:text-[#e88d35] disabled:opacity-50" title="Download searchable PDF"><Download size={16} /></button>}
      {doc.status === 'completed' && <button onClick={() => setEditing(true)} className="text-slate-400 hover:text-[#e88d35]" title="Review metadata"><Edit3 size={16} /></button>}
      {doc.status === 'failed' && <button onClick={() => void api.retryDocument(doc.id).then(() => dispatch(invalidateDocuments()))} className="text-slate-400 hover:text-[#e88d35]" title="Retry processing"><RefreshCw size={16} /></button>}
      <button disabled={deleting} onClick={() => void deleteDocument()} className="text-slate-400 hover:text-red-600 disabled:opacity-50" title="Delete document" aria-label={`Delete ${doc.filename}`}><Trash2 size={16} /></button>
    </div>
    {showUncertain && <div className="mt-4 border-t border-amber-100 pt-3"><p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-700">Uncertain OCR regions</p>{regions.length ? <div className="grid gap-2">{regions.map((region) => <div key={region.id} className="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2"><textarea value={regionDrafts[region.id] ?? region.text} onChange={(event) => setRegionDrafts({ ...regionDrafts, [region.id]: event.target.value })} className="w-full resize-none bg-transparent text-sm text-slate-700 outline-none" rows={2} /><div className="mt-1 flex items-center justify-between"><span className="text-[10px] text-amber-700">Page {region.page_number} · {Math.round((region.confidence ?? 0) * 100)}% confidence</span><button onClick={() => void saveRegion(region)} className="flex items-center gap-1 text-[10px] font-bold text-[#d37d2c]"><Save size={12} />Save correction</button></div></div>)}</div> : <p className="text-xs text-slate-500">No uncertain regions were returned.</p>}</div>}
  </div>
}
