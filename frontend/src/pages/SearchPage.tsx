import { Search, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import type { DocumentRecord } from '../api'
import { api, getApiError } from '../api'

export function SearchPage() {
  const [filters, setFilters] = useState({ query: '', document_number: '', issuing_office: '', date_from: '', date_to: '' })
  const [results, setResults] = useState<DocumentRecord[]>([])
  const [total, setTotal] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await api.searchRecords(filters)
      setResults(response.items)
      setTotal(response.total)
    } catch (err) {
      setError(getApiError(err, 'Could not search the digitised records.'))
    } finally {
      setBusy(false)
    }
  }
  return <div className="space-y-7">
    <div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">RECORD SEARCH</p><h1 className="mt-2 font-serif text-4xl font-medium tracking-tight text-[#17233b]">Find a government record</h1><p className="mt-2 text-sm text-slate-500">Search verified metadata by subject, reference number, office, or date.</p></div>
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <label className="flex items-center gap-3 border-b border-slate-100 pb-4 text-sm text-slate-500"><Search size={18} /><input value={filters.query} onChange={(event) => setFilters({ ...filters, query: event.target.value })} placeholder="Subject, reference number, office, or filename" className="w-full outline-none" /></label>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <input aria-label="Reference number" value={filters.document_number} onChange={(event) => setFilters({ ...filters, document_number: event.target.value })} placeholder="Reference number" className="rounded-lg border border-slate-200 px-3 py-2 text-sm" />
        <input aria-label="Issuing office" value={filters.issuing_office} onChange={(event) => setFilters({ ...filters, issuing_office: event.target.value })} placeholder="Issuing office" className="rounded-lg border border-slate-200 px-3 py-2 text-sm" />
        <label className="text-xs text-slate-500">Date from<input aria-label="Date from" type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label>
        <label className="text-xs text-slate-500">Date to<input aria-label="Date to" type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm" /></label>
      </div>
      <button disabled={busy} className="mt-4 flex items-center gap-2 rounded-lg bg-[#e88d35] px-4 py-2.5 text-xs font-bold text-white disabled:opacity-50"><SlidersHorizontal size={14} />{busy ? 'Searching…' : 'Search records'}</button>
    </form>
    {error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">{error}</p>}
    <p className="text-xs text-slate-400">{total} matching records</p>
    <div className="space-y-3">{results.map((document) => <article key={document.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-start justify-between gap-4"><div><h2 className="text-sm font-bold text-slate-700">{document.subject || document.filename}</h2><p className="mt-1 text-xs text-slate-500">{document.issuing_office || 'Issuing office not detected'}</p></div><span className="text-xs text-slate-400">{document.document_date || 'Date not detected'}</span></div><div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500"><span className="rounded bg-slate-100 px-2 py-1">{document.document_number || 'No reference number'}</span><span className={`rounded px-2 py-1 ${document.metadata_status === 'verified' ? 'bg-teal-50 text-teal-700' : 'bg-amber-50 text-amber-700'}`}>{document.metadata_status === 'verified' ? 'Verified metadata' : 'Needs review'}</span></div></article>)}</div>
  </div>
}
