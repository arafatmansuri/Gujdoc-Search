import { AuthForm } from '../components/AuthForm'
export function LoginPage({ onAuthenticated }: { onAuthenticated: (access: string, refresh: string, email: string) => void }) { return <AuthForm mode="login" onAuthenticated={onAuthenticated} /> }
