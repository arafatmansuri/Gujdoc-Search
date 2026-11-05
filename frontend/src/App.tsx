import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api'
import { AppLayout } from './components/AppLayout'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { RegisterPage } from './pages/RegisterPage'
import { SearchPage } from './pages/SearchPage'
import { DocumentDetailPage } from './pages/DocumentDetailPage'
import { AdminPage } from './pages/AdminPage'

export default function App() {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'reviewer' | 'admin'>('reviewer')
  const [token, setToken] = useState(() => localStorage.getItem('gujdoc_access_token'))

  useEffect(() => {
    if (!token) return
    api.me().then((user) => { setEmail(user.email); setRole(user.role) }).catch(() => {
      localStorage.removeItem('gujdoc_access_token')
      setToken(null)
    })
  }, [token])

  const signIn = (accessToken: string, refreshToken: string, userEmail: string) => {
    localStorage.setItem('gujdoc_access_token', accessToken)
    localStorage.setItem('gujdoc_refresh_token', refreshToken)
    setEmail(userEmail)
    setToken(accessToken)
  }

  const signOut = async () => {
    const refreshToken = localStorage.getItem('gujdoc_refresh_token')
    if (refreshToken) await api.logout(refreshToken).catch(() => undefined)
    localStorage.removeItem('gujdoc_access_token')
    localStorage.removeItem('gujdoc_refresh_token')
    setToken(null)
  }

  return <Routes>
    <Route path="/login" element={token ? <Navigate to="/" replace /> : <LoginPage onAuthenticated={signIn} />} />
    <Route path="/register" element={token ? <Navigate to="/" replace /> : <RegisterPage onAuthenticated={signIn} />} />
    <Route element={token ? <AppLayout email={email} role={role} onLogout={signOut} /> : <Navigate to="/login" replace />}>
      <Route index element={<HomePage />} />
      <Route path="/profile" element={<ProfilePage email={email} />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/documents/:id" element={<DocumentDetailPage />} />
      {role === 'admin' && <Route path="/admin" element={<AdminPage />} />}
    </Route>
    <Route path="*" element={<Navigate to={token ? '/' : '/login'} replace />} />
  </Routes>
}
