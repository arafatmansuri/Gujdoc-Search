import { AuthForm } from '../components/AuthForm'
export function RegisterPage({ onAuthenticated }: { onAuthenticated: (access: string, refresh: string, email: string) => void }) { return <AuthForm mode="register" onAuthenticated={onAuthenticated} /> }
