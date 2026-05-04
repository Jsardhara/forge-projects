import { RiskGauge } from "@/components/RiskGauge";
import { IncidentTimeline } from "@/components/IncidentTimeline";
import { EscortWindow } from "@/components/EscortWindow";
import { OperatorList } from "@/components/OperatorList";
import { SubscribeForm } from "@/components/SubscribeForm";
import { loadEscorts, loadIncidents, loadOperators } from "@/lib/dataStore";
import { assessRisk } from "@/lib/risk";
import { formatLocalDate } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [incidents, operators, escorts] = await Promise.all([
    loadIncidents(),
    loadOperators(),
    loadEscorts(),
  ]);
  const lastUpdated = incidents[0]?.timestamp ?? new Date().toISOString();
  // Assess relative to the most recent incident so a static seed dataset still
  // surfaces a meaningful risk level. Live deployments with current data will
  // see real-time wall-clock assessment because the latest timestamp will be
  // within the last 24h anyway.
  const wallNow = new Date();
  const latestTs = Date.parse(lastUpdated);
  const effectiveNow = Number.isFinite(latestTs) && latestTs > wallNow.getTime()
    ? new Date(latestTs)
    : wallNow;
  const risk = assessRisk(incidents, effectiveNow);

  return (
    <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-10 md:py-16">
      <header className="flex flex-wrap items-end justify-between gap-4 pb-8">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-bone-200/50">
            Hormuz Transit Advisor
          </p>
          <h1 className="mt-2 text-2xl md:text-3xl font-semibold text-bone-50 max-w-2xl leading-tight">
            One page. Is the strait passable right now?
          </h1>
        </div>
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-widest text-bone-200/50">
            Last update
          </div>
          <div className="font-mono text-xs text-bone-100">
            {formatLocalDate(lastUpdated)}
          </div>
        </div>
      </header>

      <RiskGauge risk={risk} />

      <div className="mt-10 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 order-2 lg:order-1">
          <IncidentTimeline incidents={incidents} limit={20} />
        </div>
        <aside className="order-1 lg:order-2 space-y-6">
          <EscortWindow escorts={escorts} />
          <OperatorList operators={operators} />
          <SubscribeForm />
        </aside>
      </div>

      <footer className="mt-16 pt-8 border-t border-white/5 text-xs text-bone-200/40">
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <span>
            Data: UKMTO · Reuters · NPR · CENTCOM. Seeded illustrative dataset for MVP.
          </span>
          <span className="font-mono">© 2026 — not investment, security, or routing advice.</span>
        </div>
      </footer>
    </main>
  );
}
