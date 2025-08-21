import './globals.css'
import { Toaster } from 'react-hot-toast'

export const metadata = {
  title: 'LayScience',
  description: 'Readable summaries of scientific PDFs',
}

export default function RootLayout({ children }: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <Toaster position="top-center" />
        {children}
      </body>
    </html>
  )
}
