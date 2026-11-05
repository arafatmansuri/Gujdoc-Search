import { FileText, RefreshCw } from 'lucide-react'
import type { DocumentRecord } from '../api'
import { api } from '../api'
import { StatusBadge } from './StatusBadge'
const date = (value?: string) => value ? new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Just now'
export function DocumentList({ documents }: { documents: DocumentRecord[] }) {
  if (!documents.length) return <div className="rounded-2xl border border-dashed border-slate-300 bg-white/50 px-5 py-14 text-center"><FileText className="mx-auto mb-3 text-[#e88d35]" /><h3 className="text-sm font-bold text-slate-700">No documents yet</h3><p className="mt-1 text-xs text-slate-400">Use “Add document” in the sidebar to upload your first PDF.</p></div>
  return <div className="space-y-2">{documents.map((doc) => <div key={doc.id} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-orange-50 text-[#df7f3b]"><FileText size={19} /></div><div className="min-w-0 flex-1"><strong className="block truncate text-sm text-slate-700">{doc.filename}</strong><span className="mt-1 block text-[10px] text-slate-400">Added {date(doc.created_at)}</span></div><StatusBadge status={doc.status} />{doc.status === 'failed' && <button onClick={() => void api.retryDocument(doc.id)} className="text-slate-400 hover:text-[#e88d35]" title="Retry processing"><RefreshCw size={16} /></button>}</div>)}</div>
}
