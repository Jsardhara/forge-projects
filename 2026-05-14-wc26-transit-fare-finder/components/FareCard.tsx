"use client";

import { Lang, t } from "@/lib/i18n";
import { RouteOption } from "@/lib/routes";
import LastReturnBadge from "./LastReturnBadge";
import { buildIcs, buildDepartureStamp } from "@/lib/ics";

interface MatchSummary {
  id: string;
  label: string;
  teams: string;
  date: string;
  kickoff: string;
  endsApprox: string;
  venue: string;
}

interface Props {
  option: RouteOption & { lastReturnWarn: boolean };
  rank: number;
  lang: Lang;
  match: MatchSummary | null;
  originName: string;
}

export default function FareCard({ option, rank, lang, match, originName }: Props) {
  const saved =
    option.originalUsd && option.originalUsd > option.priceUsd
      ? option.originalUsd - option.priceUsd
      : 0;

  const handleIcsDownload = () => {
    if (!match) return;
    const { stamp, readable } = buildDepartureStamp(
      match.date,
      match.kickoff,
      option.doorMinutes,
    );
    const ics = buildIcs({
      uid: `${option.mode}-${match.id}-${stamp}@wc26-fare-finder`,
      title: `Depart for ${match.venue}: ${option.modeLabel}`,
      description: `Leave ${originName} for ${match.venue}. ${option.pathSummary}. Kickoff ${match.kickoff} (${match.label}, ${match.teams}). Door-to-door ${option.doorMinutes} min.`,
      location: originName,
      startLocal: stamp,
      durationMinutes: option.doorMinutes,
    });
    const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wc26-${match.id}-${option.mode}-depart-${readable.replace(/[^0-9]/g, "")}.ics`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const reliabilityColor =
    option.reliability === "high"
      ? "bg-electric/20 text-electric"
      : option.reliability === "medium"
        ? "bg-gold/20 text-gold"
        : "bg-flame/20 text-flame";

  return (
    <article className="card-edge group relative flex flex-col gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.06] via-white/[0.02] to-transparent p-5 transition-all hover:border-white/20">
      <header className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] text-white/40">
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 font-semibold text-white/70">
              #{rank}
            </span>
            <span>{option.mode.replace("_", " ")}</span>
          </div>
          <h3 className="mt-2 font-display text-xl font-semibold leading-tight">
            {option.modeLabel}
          </h3>
        </div>
        <div className="text-right">
          <div className="font-display text-3xl font-bold tracking-tight text-chalk">
            ${option.priceUsd}
          </div>
          {saved > 0 && (
            <div className="mt-0.5 text-[10px] uppercase tracking-widest text-electric">
              {t(lang, "savedVs")}: <span className="font-bold">${saved}</span>
            </div>
          )}
          {option.originalUsd && option.originalUsd > option.priceUsd && (
            <div className="text-[10px] text-white/40 line-through">
              ${option.originalUsd}
            </div>
          )}
        </div>
      </header>

      <p className="text-sm leading-snug text-white/70">{option.pathSummary}</p>

      <dl className="grid grid-cols-3 gap-3 border-t border-white/5 pt-4 text-xs">
        <div>
          <dt className="uppercase tracking-widest text-white/40">
            {t(lang, "doorTime")}
          </dt>
          <dd className="mt-1 font-display text-lg font-semibold text-chalk">
            {option.doorMinutes}{" "}
            <span className="text-xs font-normal text-white/50">
              {t(lang, "minutes")}
            </span>
          </dd>
        </div>
        <div>
          <dt className="uppercase tracking-widest text-white/40">
            {t(lang, "transfers")}
          </dt>
          <dd className="mt-1 font-display text-lg font-semibold text-chalk">
            {option.transfers}
          </dd>
        </div>
        <div>
          <dt className="uppercase tracking-widest text-white/40">
            {t(lang, "reliability")}
          </dt>
          <dd className="mt-1">
            <span
              className={
                "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest " +
                reliabilityColor
              }
            >
              {t(lang, option.reliability)}
            </span>
          </dd>
        </div>
      </dl>

      <footer className="mt-auto flex items-center justify-between gap-2 pt-2">
        <div className="flex flex-wrap items-center gap-1">
          {option.lastReturnWarn && <LastReturnBadge lang={lang} />}
        </div>
        {match && (
          <button
            type="button"
            onClick={handleIcsDownload}
            className="focus-ring rounded-full border border-electric/40 bg-electric/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest text-electric transition-colors hover:bg-electric/20"
          >
            {t(lang, "addToCalendar")}
          </button>
        )}
      </footer>
    </article>
  );
}
