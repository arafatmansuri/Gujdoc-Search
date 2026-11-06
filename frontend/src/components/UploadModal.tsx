import { CircleAlert, FileText, LoaderCircle, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { api, getApiError, type DocumentRecord } from '../api'

export function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: (document: DocumentRecord) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function selectFile(file?: File) {
    if (!file) return
    setError('')
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(undefined)
      setError('Please choose a valid PDF file.')
      return
    }
    setSelectedFile(file)
  }

  async function upload() {
    if (!selectedFile) return
    setBusy(true); setError('')
    try { const document = await api.upload(selectedFile); onUploaded(document); onClose() } catch (err) { setError(getApiError(err, 'Upload failed. Please choose a valid PDF.')) } finally { setBusy(false) }
  }
  return <div className="fixed inset-0 z-30 grid place-items-center bg-slate-950/40 p-4" onClick={() => !busy && onClose()}>
    <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}>
      <div className="mb-6 flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">DOCUMENT LIBRARY</p><h2 className="mt-1 font-serif text-2xl font-medium text-[#17233b]">Add a document</h2></div><button disabled={busy} onClick={onClose} aria-label="Close" className="disabled:opacity-40"><X size={19} className="text-slate-400" /></button></div>
      <button disabled={busy} onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]) }} className="flex w-full flex-col items-center rounded-xl border-2 border-dashed border-slate-200 px-5 py-12 text-center hover:border-[#e88d35] hover:bg-orange-50/30 disabled:opacity-60"><UploadCloud className="mb-3 text-[#e88d35]" size={29} /><strong className="text-sm text-slate-700">{busy ? 'Uploading your PDF…' : selectedFile ? 'PDF ready to upload' : 'Drop your PDF here'}</strong><span className="mt-1 text-xs text-slate-400">{busy ? 'Please wait while we process your document' : 'or click to browse · PDF only'}</span></button>
      <input ref={inputRef} hidden type="file" accept=".pdf,application/pdf" onChange={(event) => { selectFile(event.target.files?.[0]); event.target.value = '' }} />
      {selectedFile && !busy && <div className="mt-4 flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2.5"><FileText size={18} className="shrink-0 text-[#e88d35]" /><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-700">{selectedFile.name}</p><p className="text-xs text-slate-400">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p></div></div>}
      {error && <p className="mt-4 flex items-center gap-2 text-xs text-red-600"><CircleAlert size={14} />{error}</p>}
      <div className="mt-6 flex justify-end gap-3"><button disabled={busy} onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-slate-500 hover:bg-slate-50 disabled:opacity-40">Cancel</button><button disabled={!selectedFile || busy} onClick={() => void upload()} className="flex items-center gap-2 rounded-lg bg-[#e88d35] px-4 py-2 text-sm font-medium text-white hover:bg-[#d97d29] disabled:cursor-not-allowed disabled:opacity-50">{busy && <LoaderCircle size={16} className="animate-spin" />}{busy ? 'Uploading…' : 'Upload document'}</button></div>
    </div>
  </div>
}
