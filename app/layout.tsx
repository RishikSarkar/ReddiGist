import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'ReddiGist',
  description: 'Extract and analyze key phrases from Reddit discussions',
  keywords: 'Reddit, text analysis, discussion summary, phrase extraction',
  openGraph: {
    title: 'ReddiGist',
    description: 'Extract and analyze key phrases from Reddit discussions',
    type: 'website',
  },
  icons: []
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="data:," />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  )
}
