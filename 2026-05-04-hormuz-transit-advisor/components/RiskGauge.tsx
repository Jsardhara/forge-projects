import type { RiskAssessment, RiskLevel } from "@/lib/types";
import { levelLabel } from "@/lib/risk";

const ALL_LEVELS: RiskLevel[] = ["GREEN", "AMBER", "RED", "BLACK"];

const LEVEL_TO_BG: Record<RiskLevel, string> = {
  GREEN: "bg-risk-green",
  AMBER: "bg-risk-amber",
  RED: "bg-risk-red",
  BLACK: "bg-risk-black",
};

const LEVEL_TO_TEXT: Record<RiskLevel, string> = {
  GREEN: "text-risk-green",
  AMBER: "text-risk-amber",
  RED: "text-risk-red",
  BLACK: "text-bone-50",
};

const LEVEL_TO_RING: Record<RiskLevel, string> = {
  GREEN: "ring-risk-green/40",
  AMBER: "ring-risk-amber/40",
  RED: "ring-risk-red/50",
  BLACK: "ring-bone-50/30",
};

export function RiskGauge({ risk }: { risk: RiskAssessment }) {
  return (
    <section
      aria-labelledby="risk-heading"
      className={`relative rounded-3xl p-6 md:p-10 bg-ink-900 ring-1 ${LEVEL_TO_RING[risk.level]} shadow-panel overflow-hidden grain`}
    >
      <div
        aria-hidden
        className={`absolute -top-32 -right-32 w-96 h-96 rounded-full blur-3xl opacity-30 ${LEVEL_TO_BG[risk.level]}`}
      />
      <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-bone-200/60">
            Strait of Hormuz · current risk
          </p>
          <h1
            id="risk-heading"
            className={`mt-3 font-mono text-6xl md:text-8xl leading-none ${LEVEL_TO_TEXT[risk.level]}`}
            data-testid="risk-level"
          >
            {risk.level}
          </h1>
          <p className="mt-2 text-bone-100 text-base md:text-lg max-w-xl">
            {levelLabel(risk.level)}
          </p>
        </div>

        <div className="md:text-right">
          <div className="text-xs uppercase tracking-[0.25em] text-bone-200/60">
            Weighted score (24h)
          </div>
          <div className="font-mono text-4xl md:text-5xl text-bone-50">
            {risk.score.toString().padStart(2, "0")}
          </div>
          <div className="mt-1 text-xs text-bone-200/60">
            {risk.weightedCount} reported events
          </div>
        </div>
      </div>

      <div className="relative mt-8">
        <div className="rule" />
        <p className="mt-4 text-sm md:text-base text-bone-100/80 leading-relaxed max-w-2xl">
          <span className="text-bone-200/60 uppercase tracking-widest text-[10px] mr-2">
            Rationale
          </span>
          {risk.rationale}
        </p>
      </div>

      <div
        role="meter"
        aria-valuenow={risk.score}
        aria-valuemin={0}
        aria-valuemax={20}
        aria-label={`Risk level ${risk.level}, score ${risk.score}`}
        className="relative mt-6 grid grid-cols-4 gap-1"
      >
        {ALL_LEVELS.map((lvl) => {
          const active = lvl === risk.level;
          return (
            <div
              key={lvl}
              className={`h-2 rounded-full transition-opacity ${LEVEL_TO_BG[lvl]} ${active ? "opacity-100" : "opacity-25"}`}
            />
          );
        })}
      </div>
      <div className="mt-2 grid grid-cols-4 gap-1 text-[10px] uppercase tracking-widest text-bone-200/50">
        {ALL_LEVELS.map((lvl) => (
          <div key={lvl}>{lvl}</div>
        ))}
      </div>
    </section>
  );
}
