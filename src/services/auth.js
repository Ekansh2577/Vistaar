const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function request(path, body) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/auth${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      credentials: 'include',
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error('Could not reach the VISTAAR server. Check that the backend is running and try again.')
  }

  let data = {}
  try { data = await response.json() } catch { /* Non-JSON error response */ }
  if (!response.ok) {
    const detail = data.detail
    const message = Array.isArray(detail)
      ? detail.map((issue) => issue.msg).join(' ')
      : detail || `Request failed (${response.status}).`
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return data
}

export const authService = {
  me: () => request('/me'),
  register: (payload) => request('/register', payload),
  login: (email, password) => request('/login', { email, password }),
  logout: () => request('/logout', {}),
  forgotPassword: (email) => request('/forgot-password', { email }),
  resetPassword: (token, password) => request('/reset-password', { token, password }),
}
