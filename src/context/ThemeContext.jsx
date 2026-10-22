import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('vistaar-theme')
    if (saved === 'enlighten' || saved === 'light') return 'enlighten'
    if (saved === 'explore' || saved === 'dark') return 'explore'
    // Default to explore (dark) as the initial immersive workspace
    return 'explore'
  })

  useEffect(() => {
    // Set both data-theme and class for full CSS compatibility
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.setAttribute('data-mode', theme === 'enlighten' ? 'enlighten' : 'explore')
    if (theme === 'enlighten') {
      document.documentElement.classList.add('theme-enlighten')
      document.documentElement.classList.remove('theme-explore')
      // Also set standard light class for legacy compatibility
      document.documentElement.setAttribute('data-theme-legacy', 'light')
    } else {
      document.documentElement.classList.add('theme-explore')
      document.documentElement.classList.remove('theme-enlighten')
      document.documentElement.setAttribute('data-theme-legacy', 'dark')
    }
    localStorage.setItem('vistaar-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'enlighten' ? 'explore' : 'enlighten'))
  }

  const setEnlighten = () => setTheme('enlighten')
  const setExplore = () => setTheme('explore')

  const isEnlighten = theme === 'enlighten'
  const isExplore = theme === 'explore'

  return (
    <ThemeContext.Provider
      value={{
        theme,
        setTheme,
        toggleTheme,
        setEnlighten,
        setExplore,
        isEnlighten,
        isExplore,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
