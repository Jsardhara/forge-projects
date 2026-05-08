import type { Metadata } from 'next';
import './globals.css';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Hantavirus Outbreak Tracker — May 2026',
  description:
    'Plain-language tracker for the May 2026 hantavirus cluster: cruise ship cases, Canary Islands, Tristan da Cunha, UK. Symptom checker, case map, and what to do if exposed.',
  openGraph: {
    title: 'Hantavirus Outbreak Tracker — May 2026',
    description: 'Symptoms, exposure check, case map, and clinician script.',
    type: 'website',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <header className="border-b border-ink/10 bg-bone/90 backdrop-blur sticky top-0 z-50">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="font-serif text-lg font-bold tracking-tight">
              Hantavirus<span className="text-rust">.</span>tracker
            </Link>
            <nav aria-label="Main" className="flex gap-4 text-sm">
              <Link href="/checker/" className="hover:underline">Check</Link>
              <Link href="/map/" className="hover:underline">Map</Link>
              <Link href="/guide/" className="hover:underline">Guide</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-ink/10 mt-12">
          <div className="max-w-5xl mx-auto px-4 py-6 text-xs text-ink/70 space-y-2">
            <p>
              <strong>Informational only — not medical advice.</strong> If you have severe symptoms,
              call emergency services or your nearest hospital.
            </p>
            <p>
              Sources:{' '}
              <a className="underline" href="https://www.cdc.gov/hantavirus/" target="_blank" rel="noopener noreferrer">CDC</a>{' '}·{' '}
              <a className="underline" href="https://www.who.int/" target="_blank" rel="noopener noreferrer">WHO</a>{' '}·{' '}
              <a className="underline" href="https://www.aljazeera.com/news/2026/5/8/hantavirus-cases-rise-on-cruise-ship-as-uk-tracks-nationals" target="_blank" rel="noopener noreferrer">Al Jazeera, 8 May 2026</a>
            </p>
            <p>Last data refresh: 2026-05-08 · Static site, edit data/*.json to update.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
