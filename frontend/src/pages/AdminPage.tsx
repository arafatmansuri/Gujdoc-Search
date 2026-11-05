import { ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, getApiError } from '../api'

export function AdminPage() {
  const [users, setUsers] = useState<Awaited<ReturnType<typeof api.listUsers>>>([])
  const [error, setError] = useState('')
  useEffect(() => { void api.listUsers().then(setUsers).catch((reason) => setError(getApiError(reason, 'Could not load users.'))) }, [])
  async function changeRole(id: number, role: 'reviewer' | 'admin') {
    const updated = await api.updateUserRole(id, role)
    setUsers((current) => current.map((user) => user.id === id ? { ...user, role: updated.role } : user))
  }
  return <div className="space-y-6"><div><p className="text-[10px] font-bold uppercase tracking-wider text-[#e88d35]">ADMINISTRATION</p><h1 className="mt-2 text-3xl font-semibold text-[#17233b]">Reviewer access</h1><p className="mt-2 text-sm text-slate-500">Manage who can verify metadata and correct OCR.</p></div>{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-400"><tr><th className="px-4 py-3">User</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Action</th></tr></thead><tbody>{users.map((user) => <tr key={user.id} className="border-t border-slate-100"><td className="px-4 py-3 text-slate-700">{user.email}</td><td className="px-4 py-3 text-xs text-slate-500">{user.is_active ? 'Active' : 'Disabled'}</td><td className="px-4 py-3"><span className="inline-flex items-center gap-1 text-xs text-slate-600"><ShieldCheck size={14} />{user.role}</span></td><td className="px-4 py-3"><select value={user.role} onChange={(event) => void changeRole(user.id, event.target.value as 'reviewer' | 'admin')} className="rounded border border-slate-200 px-2 py-1 text-xs"><option value="reviewer">Reviewer</option><option value="admin">Admin</option></select></td></tr>)}</tbody></table></div></div>
}
