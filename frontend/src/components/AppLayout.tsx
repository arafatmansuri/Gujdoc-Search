import { BookOpen, FilePlus2, House, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { ProfileMenu } from './ProfileMenu'
import { Logo } from './Logo'
import { UploadModal } from './UploadModal'

export function AppLayout({ email, onLogout }: { email: string; onLogout: () => void }) {
  const [menu, setMenu] = useState(false)
  const [upload, setUpload] = useState(false)
  const location = useLocation()
  return <div className="min-h-screen bg-[#f7f5ef] text-[#17233b]">
    <aside className={`fixed inset-y-0 left-0 z-20 w-64 bg-[#17233b] p-6 transition-transform lg:translate-x-0 ${menu ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex items-center justify-between"><Logo /><button className="text-slate-400 lg:hidden" onClick={() => setMenu(false)}><X size={20} /></button></div>
      <p className="mt-12 px-2 text-[10px] font-bold uppercase tracking-[.15em] text-slate-400">Workspace</p>
      <nav className="mt-3 space-y-1">
        <NavLink to="/" end onClick={() => setMenu(false)} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-3 text-sm ${isActive ? 'bg-[#273450] text-white' : 'text-slate-300 hover:bg-[#273450]'}`}><House size={17} />Home</NavLink>
        <button onClick={() => setUpload(true)} className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm text-slate-300 hover:bg-[#273450]"><FilePlus2 size={17} />Add document</button>
        <NavLink to="/profile" onClick={() => setMenu(false)} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-3 text-sm ${isActive ? 'bg-[#273450] text-white' : 'text-slate-300 hover:bg-[#273450]'}`}><BookOpen size={17} />Profile settings</NavLink>
      </nav>
      <div className="absolute bottom-6 left-6 right-6 border-t border-white/10 pt-4 text-xs text-slate-400">Private document intelligence</div>
    </aside>
    <div className="lg:pl-64"><header className="flex h-20 items-center justify-between border-b border-slate-200 bg-[#f7f5ef]/90 px-5 backdrop-blur lg:px-10"><button className="lg:hidden" onClick={() => setMenu(true)}><Menu size={21} /></button><div className="hidden text-sm font-medium text-slate-500 lg:block">{location.pathname === '/profile' ? 'Profile settings' : 'Your research desk'}</div><div className="ml-auto"><ProfileMenu email={email} onLogout={onLogout} /></div></header><main className="mx-auto max-w-6xl px-5 py-8 lg:px-10"><Outlet /></main></div>
    {upload && <UploadModal onClose={() => setUpload(false)} onUploaded={() => window.dispatchEvent(new Event('documents-refresh'))} />}
  </div>
}
