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
  metadataBase: new URL('https://reddi-gist.vercel.app'),
  openGraph: {
    title: 'ReddiGist',
    description: 'Extract and analyze key phrases from Reddit discussions',
    type: 'website',
    images: [
      {
        url: '/reddigist-logo-nobg.png',
        width: 500,
        height: 500,
        alt: 'ReddiGist',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ReddiGist',
    description: 'Extract and analyze key phrases from Reddit discussions',
    images: ['/reddigist-logo-nobg.png'],
  },
  icons: {
    icon: '/reddigist-logo-nobg.png',
    shortcut: '/reddigist-logo-nobg.png',
    apple: '/reddigist-logo-nobg.png',
  }
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={ibmPlexSans.className}>{children}</body>
    </html>
  )
}
