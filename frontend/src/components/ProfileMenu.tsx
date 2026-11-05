import { LogOut, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

export function ProfileMenu({ email, onLogout }: { email: string; onLogout: () => void }) {
  return <details className="relative">
    <summary className="flex list-none items-center gap-2 rounded-full border border-slate-200 bg-white p-1.5 shadow-sm hover:border-[#e88d35]">
      <span className="grid h-8 w-8 place-items-center rounded-full bg-[#f7dfc2] text-sm font-bold text-[#9b5b25]">{email.charAt(0).toUpperCase()}</span>
    </summary>
    <div className="absolute right-0 top-12 z-20 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-xl">
      <p className="truncate px-2 py-2 text-xs text-slate-500">{email}</p>
      <Link to="/profile" className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-slate-700 hover:bg-slate-50"><UserRound size={15} />Profile settings</Link>
      <button onClick={onLogout} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-red-600 hover:bg-red-50"><LogOut size={15} />Log out</button>
    </div>
  </details>
}
