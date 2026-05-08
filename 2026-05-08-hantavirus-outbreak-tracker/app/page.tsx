import Link from 'next/link';
import clusters from '../data/clusters.json';

export default function Home() {
  const confirmed = clusters.reduce((s, c) => s + c.cases, 0);
  const suspected = clusters.reduce((s, c) => s + c.suspected, 0);
  const sites = clusters.length;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 md:py-16">
      <p className="text-xs uppercase tracking-widest text-rust font-semibold mb-3">
        Outbreak update — 8 May 2026
      </p>
      <h1 className="font-serif text-4xl md:text-6xl font-bold leading-[1.05] tracking-tight max-w-3xl">
        Hantavirus is spreading from a cruise ship. Here's what's known, in plain English.
      </h1>
      <p className="mt-6 text-lg md:text-xl text-ink/80 max-w-2xl">
        Confirmed cases on the <em>MV Atlantic Voyager</em>, suspected cases on Tristan da Cunha and
        in the Canary Islands, and the UK is tracking returning travelers. This page tells you what
        symptoms to watch for, whether you were exposed, and what to do next.
      </p>

      <div className="mt-10 grid grid-cols-3 gap-4 md:gap-8 max-w-2xl">
        <Stat value={confirmed} label="Confirmed cases" tone="rust" />
        <Stat value={suspected} label="Suspected" tone="amber" />
        <Stat value={sites} label="Active sites" tone="moss" />
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <CTA href="/checker/" primary>Check my symptoms →</CTA>
        <CTA href="/map/">See case map</CTA>
        <CTA href="/guide/">What to do if exposed</CTA>
      </div>

      <section className="mt-16 grid md:grid-cols-2 gap-6">
        <Card title="What is hantavirus?">
          <p>
            A family of viruses spread by rodents — mostly through aerosolized urine, droppings, or
            saliva. Two main syndromes: <strong>HPS</strong> (Hantavirus Pulmonary Syndrome — lungs)
            and <strong>HFRS</strong> (Hemorrhagic Fever with Renal Syndrome — kidneys). The current
            cluster is being investigated as a novel ship-borne strain with rare close-quarters
            person-to-person spread.
          </p>
        </Card>
        <Card title="Symptoms to know">
          <ul className="list-disc list-inside space-y-1">
            <li>Sudden fever, severe muscle aches (thighs, back)</li>
            <li>Headache, chills, nausea</li>
            <li>After 4–10 days: shortness of breath, cough — emergency</li>
            <li>Some strains: low urine output, blurred vision (kidney)</li>
          </ul>
        </Card>
        <Card title="Who's most at risk">
          <ul className="list-disc list-inside space-y-1">
            <li>Passengers and crew of MV Atlantic Voyager (28 Apr–12 May 2026)</li>
            <li>Port workers in Funchal, Tenerife, Las Palmas</li>
            <li>Tristan da Cunha residents and recent visitors</li>
            <li>Healthcare workers caring for confirmed cases</li>
          </ul>
        </Card>
        <Card title="Trust the sources, not the chatter">
          <p>
            Every claim on this page links to CDC, WHO, UKHSA, or major news. We don't run ads, set
            cookies, or collect any data. Open source, edit and share freely.
          </p>
        </Card>
      </section>

      <section className="mt-16 border-t border-ink/10 pt-10">
        <h2 className="font-serif text-2xl font-bold mb-4">Active clusters at a glance</h2>
        <ul className="divide-y divide-ink/10 border border-ink/10 rounded-lg overflow-hidden bg-white/40">
          {clusters.map((c) => (
            <li key={c.id} className="p-4 flex flex-col md:flex-row md:items-center gap-2 md:gap-6">
              <span
                className={`text-xs font-semibold uppercase tracking-wide px-2 py-1 rounded ${
                  c.status === 'confirmed'
                    ? 'bg-rust text-bone'
                    : c.status === 'suspected'
                    ? 'bg-amber text-ink'
                    : 'bg-moss text-bone'
                }`}
              >
                {c.status}
              </span>
              <span className="font-medium flex-1">{c.location}</span>
              <span className="text-sm text-ink/70">
                {c.cases} confirmed · {c.suspected} suspected
              </span>
              <a
                href={c.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm underline text-rust"
              >
                source ↗
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Stat({ value, label, tone }: { value: number; label: string; tone: string }) {
  const color =
    tone === 'rust' ? 'text-rust' : tone === 'amber' ? 'text-amber' : 'text-moss';
  return (
    <div>
      <div className={`font-serif text-4xl md:text-5xl font-bold ${color}`}>{value}</div>
      <div className="text-xs uppercase tracking-widest text-ink/60 mt-1">{label}</div>
    </div>
  );
}

function CTA({
  href,
  children,
  primary,
}: {
  href: string;
  children: React.ReactNode;
  primary?: boolean;
}) {
  const cls = primary
    ? 'bg-ink text-bone hover:bg-rust'
    : 'border border-ink/20 hover:border-ink hover:bg-ink hover:text-bone';
  return (
    <Link
      href={href}
      className={`inline-flex items-center px-5 py-3 rounded-md font-medium transition-colors ${cls}`}
    >
      {children}
    </Link>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-ink/10 rounded-lg p-5 bg-white/40">
      <h3 className="font-serif text-xl font-bold mb-2">{title}</h3>
      <div className="text-sm text-ink/80 leading-relaxed">{children}</div>
    </div>
  );
}
