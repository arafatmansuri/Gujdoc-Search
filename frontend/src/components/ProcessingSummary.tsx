import { Activity, CheckCircle2, Clock3, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../api'

export function ProcessingSummary() {
  const [metrics, setMetrics] = useState<Awaited<ReturnType<typeof api.metrics>> | null>(null)
  const [evaluation, setEvaluation] = useState<Awaited<ReturnType<typeof api.evaluationMetrics>> | null>(null)
  useEffect(() => {
    void Promise.all([api.metrics(), api.evaluationMetrics()])
      .then(([summary, evaluationSummary]) => { setMetrics(summary); setEvaluation(evaluationSummary) })
      .catch(() => undefined)
  }, [])
  if (!metrics) return null
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
    <Metric icon={<CheckCircle2 size={16} />} label="Completed" value={metrics.completed_documents} />
    <Metric icon={<Activity size={16} />} label="Average OCR" value={`${Math.round(metrics.average_ocr_confidence * 100)}%`} />
    <Metric icon={<TriangleAlert size={16} />} label="Needs review" value={metrics.uncertain_regions} />
    <Metric icon={<Clock3 size={16} />} label="Avg processing" value={`${metrics.average_processing_seconds.toFixed(1)}s`} />
    {evaluation?.ocr_character_error_rate != null && <Metric icon={<Activity size={16} />} label="Verified CER" value={`${Math.round(evaluation.ocr_character_error_rate * 100)}%`} />}
    {evaluation?.search_success_rate != null && <Metric icon={<CheckCircle2 size={16} />} label="Search success" value={`${Math.round(evaluation.search_success_rate * 100)}%`} />}
  </div>
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"><div className="flex items-center gap-2 text-[#2b8a83]">{icon}<span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</span></div><strong className="mt-1 block text-xl text-[#17233b]">{value}</strong></div>
}
