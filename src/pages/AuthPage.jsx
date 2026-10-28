import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, BookOpenCheck, FileText, Network, Quote, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/auth'

const evidence = [
  { label: 'Research paper', detail: 'Retrieval augmented generation', kind: 'paper' },
  { label: 'Methods · p. 04', detail: 'Hybrid search retrieves relevant passages', kind: 'quote' },
  { label: 'Connected concept', detail: 'Semantic indexing', kind: 'concept' },
]

export default function AuthPage({ mode = 'login' }) {
  const isSignup = mode === 'signup'
  const isForgot = mode === 'forgot-password'
  const isReset = mode === 'reset-password'
  const location = useLocation()
  const [notice, setNotice] = useState(location.state?.notice || '')
  const [busy, setBusy] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const handleSubmit = async (event) => {
    event.preventDefault()
    setNotice('')
    setBusy(true)
    const form = new FormData(event.currentTarget)
    const email = String(form.get('email') || '')
    const password = String(form.get('password') || '')
    try {
      if (isSignup) {
        await register(String(form.get('full_name') || ''), email, password)
        navigate('/', { replace: true })
      } else if (mode === 'login') {
        await login(email, password)
        const from = location.state?.from
        const destination = from ? `${from.pathname || '/'}${from.search || ''}${from.hash || ''}` : '/'
        navigate(destination, { replace: true })
      } else if (isForgot) {
        const result = await authService.forgotPassword(email)
        setNotice(result.message)
      } else if (isReset) {
        await authService.resetPassword(searchParams.get('token') || '', password)
        navigate('/login', { replace: true, state: { notice: 'Password updated. Sign in with your new password.' } })
      }
    } catch (error) {
      setNotice(error.message)
    } finally {
      setBusy(false)
    }
  }

  const title = isSignup ? 'Make room for insight.' : isForgot || isReset ? 'Recover your access.' : 'Pick up where you left off.'
  const eyebrow = isSignup ? 'START YOUR LIBRARY' : isForgot || isReset ? 'ACCOUNT RECOVERY' : 'WELCOME BACK'

  return (
    <main className="auth-page">
      <header className="auth-header">
        <Link to="/" className="auth-wordmark" aria-label="VISTAAR home">
          <span className="auth-mark"><BookOpenCheck size={19} /></span>
          <span>VISTAAR</span>
        </Link>
        <span className="auth-header-note">DOCUMENT INTELLIGENCE WORKSPACE</span>
      </header>

      <div className="auth-body">
        <section className="auth-story" aria-label="Explore evidence across your documents">
          <div className="auth-kicker"><span /> A clearer path through your sources</div>
          <h1>Ideas are stronger<br />when you can <em>trace them.</em></h1>
          <p className="auth-story-copy">Bring your documents together. Follow the connections. Find the evidence behind every answer.</p>

          <div className="evidence-map" aria-label="Example of evidence connected across a research paper">
            <div className="evidence-map-heading"><span>FIELD NOTE 01</span><span>3 linked passages</span></div>
            <div className="evidence-map-content">
              <div className="evidence-spine" aria-hidden="true"><i /><i /><i /></div>
              <div className="evidence-items">
                {evidence.map((item, index) => <div className={`evidence-item ${item.kind}`} key={item.kind}>
                  <span className="evidence-index">0{index + 1}</span>
                  <span className="evidence-item-copy"><b>{item.label}</b><small>{item.detail}</small></span>
                  {item.kind === 'paper' ? <FileText size={17} /> : item.kind === 'quote' ? <Quote size={16} /> : <Network size={17} />}
                </div>)}
              </div>
            </div>
            <div className="evidence-map-footer"><span className="evidence-dot" /> Evidence linked across your library</div>
          </div>
          <div className="auth-story-foot"><span>01 / 03</span><span>Source → passage → insight</span></div>
        </section>

        <section className="auth-panel" aria-labelledby="auth-title">
          <div className="auth-form-topline"><span>{eyebrow}</span><span>V · 01</span></div>
          <div className="auth-form-intro">
            <h2 id="auth-title">{title}</h2>
            <p>{isSignup ? 'Create a workspace for the ideas inside your documents.' : isForgot ? 'Enter your account email to receive a secure recovery link.' : isReset ? 'Choose a new password for your VISTAAR account.' : 'Your sources and discoveries are waiting.'}</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            {isSignup && <label>Full name<input name="full_name" autoComplete="name" placeholder="Your name" required maxLength={100} /></label>}
            {!isForgot && !isReset && <label>Work or school email<input name="email" type="email" autoComplete="email" placeholder="you@example.com" required maxLength={254} /></label>}
            {isForgot && <label>Work or school email<input name="email" type="email" autoComplete="email" placeholder="you@example.com" required maxLength={254} /></label>}
            {!isForgot && <label>Password<input name="password" type="password" autoComplete={isSignup || isReset ? 'new-password' : 'current-password'} placeholder={isSignup || isReset ? 'At least 8 characters' : 'Your password'} minLength={8} maxLength={128} required /></label>}
            {!isSignup && !isForgot && <div className="auth-form-aside"><label className="auth-check"><input type="checkbox" /> <span>Keep me signed in</span></label><Link className="auth-text-button" to="/forgot-password">Forgot password?</Link></div>}
            <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : isSignup ? 'Create workspace' : isForgot ? 'Send recovery link' : isReset ? 'Update password' : 'Sign in'} <ArrowUpRight size={17} /></button>
            {notice && <p className="auth-notice" role="status">{notice}</p>}
          </form>

          {isForgot || isReset ? <Link className="auth-help-link" to="/login">← Back to sign in</Link> : <>
            <p className="auth-switch">{isSignup ? 'Already have a workspace?' : 'New to VISTAAR?'} <Link to={isSignup ? '/login' : '/signup'}>{isSignup ? 'Sign in' : 'Create an account'}</Link></p>
          </>}
          <div className="auth-privacy"><ShieldCheck size={15} /> Your sources stay yours. Evidence stays traceable.</div>
        </section>
      </div>
      <footer className="auth-footer"><span>VISTAAR · RESEARCH, WITH RECEIPTS.</span><span>EXPLORE WIDELY. CITE PRECISELY.</span></footer>
    </main>
  )
}
