import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authService } from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState('')

  const refreshSession = useCallback(async () => {
    try {
      const result = await authService.me()
      setUser(result.user)
      setAuthError('')
      return result.user
    } catch (error) {
      if (error.status === 401) {
        setUser(null)
        setAuthError('')
        return null
      }
      setAuthError(error.message)
      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshSession().catch(() => {})
  }, [refreshSession])

  const login = useCallback(async (email, password) => {
    const result = await authService.login(email, password)
    setUser(result.user)
    setAuthError('')
    return result.user
  }, [])

  const register = useCallback(async (fullName, email, password) => {
    const result = await authService.register({ full_name: fullName, email, password })
    setUser(result.user)
    setAuthError('')
    return result.user
  }, [])

  const logout = useCallback(async () => {
    await authService.logout()
    setUser(null)
    setAuthError('')
  }, [])

  const value = useMemo(() => ({ user, loading, authError, login, register, logout, refreshSession }), [user, loading, authError, login, register, logout, refreshSession])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
