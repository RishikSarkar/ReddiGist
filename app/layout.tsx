import './globals.css'
import { IBM_Plex_Sans } from 'next/font/google'

const ibmPlexSans = IBM_Plex_Sans({
  weight: ['400', '500', '600', '700'],
  subsets: ['latin'],
  display: 'swap',
})

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
      <body className={ibmPlexSans.className}>{children}</body>
    </html>
  )
}
