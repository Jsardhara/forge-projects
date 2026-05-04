import type { Incident, IncidentKind } from "@/lib/types";
import { formatLocalDate, relativeTime } from "@/lib/format";

const KIND_LABEL: Record<IncidentKind, string> = {
  attack: "Attack",
  "missile-near-miss": "Near miss",
  advisory: "Advisory",
  escort: "Escort",
};

const KIND_COLOR: Record<IncidentKind, string> = {
  attack: "bg-risk-red text-bone-50",
  "missile-near-miss": "bg-risk-amber text-ink-950",
  advisory: "bg-bone-200 text-ink-950",
  escort: "bg-emerald-700 text-bone-50",
};

export function IncidentTimeline({
  incidents,
  limit = 20,
}: {
  incidents: ReadonlyArray<Incident>;
  limit?: number;
}) {
  const items = incidents.slice(0, limit);

  return (
    <section
      aria-labelledby="timeline-heading"
      className="rounded-3xl bg-ink-900 ring-1 ring-white/5 shadow-panel p-6 md:p-8"
    >
      <header className="flex items-baseline justify-between">
        <h2
          id="timeline-heading"
          className="font-mono uppercase tracking-[0.25em] text-xs text-bone-200/70"
        >
          Incident timeline
        </h2>
        <span className="text-xs text-bone-200/50">
          last {items.length} of {incidents.length}
        </span>
      </header>

      <ol className="mt-6 relative">
        <div
          aria-hidden
          className="absolute left-[7px] top-2 bottom-2 w-px bg-gradient-to-b from-transparent via-bone-200/15 to-transparent"
        />
        {items.map((it) => (
          <li key={it.id} className="relative pl-10 pb-8 last:pb-0">
            <span
              aria-hidden
              className={`absolute left-0 top-1.5 w-4 h-4 rounded-full ring-4 ring-ink-900 ${KIND_COLOR[it.kind].split(" ")[0]}`}
            />
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span
                className={`inline-flex items-center text-[10px] uppercase tracking-widest font-mono px-2 py-0.5 rounded-full ${KIND_COLOR[it.kind]}`}
              >
                {KIND_LABEL[it.kind]}
              </span>
              <time
                dateTime={it.timestamp}
                title={formatLocalDate(it.timestamp)}
                className="text-xs text-bone-200/60 font-mono"
              >
                {relativeTime(it.timestamp)}
              </time>
              {it.location && (
                <span className="text-xs text-bone-200/40 font-mono">
                  · {it.location}
                </span>
              )}
            </div>
            <h3 className="mt-2 text-bone-50 text-base md:text-lg leading-snug">
              <a
                href={it.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-bone-200 underline decoration-bone-200/20 underline-offset-4 hover:decoration-bone-200/60 transition-colors"
              >
                {it.title}
              </a>
            </h3>
            {it.summary && (
              <p className="mt-1 text-sm text-bone-100/70 leading-relaxed max-w-2xl">
                {it.summary}
              </p>
            )}
            <div className="mt-2 text-[11px] uppercase tracking-widest text-bone-200/40">
              {it.source}
              {it.vessel && <span> · {it.vessel}</span>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
