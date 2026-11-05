import { Check, CircleAlert, Clock3 } from 'lucide-react'
import type { DocumentStatus } from '../api'

const labels: Record<DocumentStatus, string> = { pending: 'Queued', processing: 'Preparing text', completed: 'Ready to ask', failed: 'Processing failed' }
export function StatusBadge({ status }: { status: DocumentStatus }) {
  const Icon = status === 'completed' ? Check : status === 'failed' ? CircleAlert : Clock3
  const colors = { completed: 'bg-teal-50 text-teal-700', failed: 'bg-red-50 text-red-600', processing: 'bg-amber-50 text-amber-700', pending: 'bg-amber-50 text-amber-700' }
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold ${colors[status]}`}><Icon size={13} />{labels[status]}</span>
}
