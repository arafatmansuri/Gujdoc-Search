import { CircleAlert, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, getApiError } from '../api'

export function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function upload(file?: File) {
    if (!file) return
    setBusy(true); setError('')
    try { await api.upload(file); onUploaded(); onClose() } catch (err) { setError(getApiError(err, 'Upload failed. Please choose a valid PDF.')) } finally { setBusy(false) }
  }
  return <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 p-4" onClick={onClose}>
    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
      <div className="mb-6 flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">DOCUMENT LIBRARY</p><h2 className="mt-1 font-serif text-2xl font-medium text-[#17233b]">Add a document</h2></div><button onClick={onClose} aria-label="Close"><X size={19} className="text-slate-400" /></button></div>
      <button disabled={busy} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); void upload(event.dataTransfer.files[0]) }} className="flex w-full flex-col items-center rounded-xl border-2 border-dashed border-slate-200 px-5 py-12 text-center hover:border-[#e88d35] hover:bg-orange-50/30 disabled:opacity-60"><UploadCloud className="mb-3 text-[#e88d35]" size={29} /><strong className="text-sm text-slate-700">{busy ? 'Uploading your PDF…' : 'Drop your PDF here'}</strong><span className="mt-1 text-xs text-slate-400">or click to browse · PDF only</span></button>
      <input ref={inputRef} hidden type="file" accept=".pdf,application/pdf" onChange={(event) => void upload(event.target.files?.[0])} />
      {error && <p className="mt-4 flex items-center gap-2 text-xs text-red-600"><CircleAlert size={14} />{error}</p>}
    </div>
  </div>
}
