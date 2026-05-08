import clusters from '../../data/clusters.json';
import ClusterMap from '../../components/ClusterMap';

export const metadata = { title: 'Case Map — Hantavirus Tracker' };

export default function MapPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-10 md:py-14">
      <p className="text-xs uppercase tracking-widest text-rust font-semibold mb-2">Live cluster map</p>
      <h1 className="font-serif text-3xl md:text-4xl font-bold leading-tight">
        Where cases and suspected cases are
      </h1>
      <p className="mt-3 text-ink/70 max-w-2xl">
        Each pin is a cluster: a city, port, ship, or settlement with reported cases. Click a pin for
        the cited source. Map data from OpenStreetMap.
      </p>

      <div className="mt-8">
        <ClusterMap />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-4 text-sm">
        <Legend color="#b3441a" label="Confirmed" />
        <Legend color="#d97706" label="Suspected" />
        <Legend color="#3d5a3a" label="Monitoring" />
      </div>

      <section className="mt-12">
        <h2 className="font-serif text-2xl font-bold mb-4">Cluster details</h2>
        <ul className="space-y-3">
          {clusters.map((c) => (
            <li key={c.id} className="border border-ink/10 rounded-lg p-4 bg-white/40">
              <div className="flex flex-wrap items-baseline gap-3">
                <h3 className="font-serif text-lg font-bold">{c.location}</h3>
                <span
                  className={`text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded ${
                    c.status === 'confirmed'
                      ? 'bg-rust text-bone'
                      : c.status === 'suspected'
                      ? 'bg-amber text-ink'
                      : 'bg-moss text-bone'
                  }`}
                >
                  {c.status}
                </span>
                <span className="text-xs text-ink/60">updated {c.updated}</span>
              </div>
              <p className="text-sm text-ink/80 mt-2">{c.note}</p>
              <p className="text-sm mt-2">
                {c.cases} confirmed · {c.suspected} suspected ·{' '}
                <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="underline text-rust">
                  {c.source_label} ↗
                </a>
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="inline-block w-3 h-3 rounded-full"
        style={{ background: color }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
