import '../styles/globals.css'
import { Toaster } from 'react-hot-toast'
import ClientProviders from '@/components/ClientProviders';

export const metadata = {
  title: process.env.NEXT_PUBLIC_APP_NAME || 'LayScience (beta)',
  description: 'Turn research papers into accurate lay summaries with evidence, in seconds.'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <div className="border-b border-border">
          <header className="container flex items-center justify-between py-4">
            <div className="text-2xl font-bold tracking-tight">
              <span style={{color: '#00BFFF'}}>Lay</span>Science <span className="text-sm opacity-70">beta — AI may be wrong</span>
            </div>
            <nav className="text-sm opacity-80">
              <a className="mr-4 hover:opacity-100" href="/">Home</a>
              <a className="hover:opacity-100" href="#about">About</a>
            </nav>
          </header>
        </div>
        <main className="container py-6">{children}</main>
        <footer className="container py-10 text-sm opacity-80">
          <div className="border-t border-border pt-6 flex items-center justify-between">
            <span>© {new Date().getFullYear()} LayScience</span>
            <span>Accent <span style={{color:'#00BFFF'}}>#00BFFF</span> • Minimalist black UI</span>
          </div>
        </footer>
        <Toaster position="top-right" />
      </body>
    </html>
  )
}
