import type { EscortWindowEntry } from "@/lib/types";
import { formatLocalDate } from "@/lib/format";

export function EscortWindow({ escorts }: { escorts: ReadonlyArray<EscortWindowEntry> }) {
  const now = Date.now();
  const upcoming = escorts
    .filter((e) => Date.parse(e.end) >= now)
    .slice(0, 4);

  return (
    <section
      aria-labelledby="escort-heading"
      className="rounded-3xl bg-ink-900 ring-1 ring-white/5 shadow-panel p-6 md:p-8"
    >
      <h2
        id="escort-heading"
        className="font-mono uppercase tracking-[0.25em] text-xs text-bone-200/70"
      >
        Next escort windows
      </h2>

      {upcoming.length === 0 ? (
        <p className="mt-4 text-sm text-bone-200/60">
          No publicly announced convoy windows. Contact UKMTO Bahrain ops cell.
        </p>
      ) : (
        <ul className="mt-5 space-y-4">
          {upcoming.map((e) => (
            <li
              key={e.id}
              className="rounded-2xl bg-ink-800/60 ring-1 ring-white/5 p-4 transition-colors hover:bg-ink-700/60"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-bone-200/60">
                  {e.authority}
                </span>
                <span className="font-mono text-xs text-bone-100">
                  {formatLocalDate(e.start)} → {formatLocalDate(e.end).slice(-12)}
                </span>
              </div>
              <p className="mt-2 text-sm text-bone-50 leading-relaxed">{e.notes}</p>
              {e.sourceUrl && (
                <a
                  href={e.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-[11px] uppercase tracking-widest text-bone-200/60 underline decoration-bone-200/20 underline-offset-4 hover:text-bone-50"
                >
                  Source
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
