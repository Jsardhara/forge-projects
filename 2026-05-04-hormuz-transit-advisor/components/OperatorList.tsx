import type { Operator } from "@/lib/types";
import { relativeTime } from "@/lib/format";

const STATUS_STYLE: Record<Operator["status"], string> = {
  suspended: "bg-risk-red/20 text-risk-red ring-risk-red/40",
  rerouted: "bg-risk-amber/15 text-risk-amber ring-risk-amber/40",
  monitoring: "bg-bone-200/10 text-bone-200 ring-bone-200/30",
};

const STATUS_LABEL: Record<Operator["status"], string> = {
  suspended: "Suspended",
  rerouted: "Rerouted",
  monitoring: "Monitoring",
};

export function OperatorList({ operators }: { operators: ReadonlyArray<Operator> }) {
  const order: Operator["status"][] = ["suspended", "rerouted", "monitoring"];
  const sorted = [...operators].sort(
    (a, b) => order.indexOf(a.status) - order.indexOf(b.status),
  );

  return (
    <section
      aria-labelledby="operators-heading"
      className="rounded-3xl bg-ink-900 ring-1 ring-white/5 shadow-panel p-6 md:p-8"
    >
      <h2
        id="operators-heading"
        className="font-mono uppercase tracking-[0.25em] text-xs text-bone-200/70"
      >
        Affected operators
      </h2>
      <p className="mt-2 text-sm text-bone-200/60">
        Public posture from major shipping lines and tanker operators.
      </p>

      <ul className="mt-5 flex flex-wrap gap-2">
        {sorted.map((o) => {
          const inner = (
            <>
              <span className="font-medium">{o.name}</span>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-widest opacity-80">
                {STATUS_LABEL[o.status]}
              </span>
              <span className="ml-2 text-[10px] opacity-50 font-mono">
                {relativeTime(o.since)}
              </span>
            </>
          );
          const className = `inline-flex items-center rounded-full px-3 py-1.5 text-sm ring-1 transition-colors ${STATUS_STYLE[o.status]}`;
          return (
            <li key={o.name}>
              {o.sourceUrl ? (
                <a
                  href={o.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`${className} hover:brightness-125`}
                >
                  {inner}
                </a>
              ) : (
                <span className={className}>{inner}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
