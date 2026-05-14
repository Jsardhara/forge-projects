"use client";

import { useMemo, useState } from "react";
import OriginPicker from "@/components/OriginPicker";
import FareCard from "@/components/FareCard";
import LangToggle from "@/components/LangToggle";
import { ORIGINS, OriginId, rankOptions, endsLate } from "@/lib/routes";
import { Lang, t } from "@/lib/i18n";
import matchesData from "@/data/matches.json";

interface MatchEntry {
  id: string;
  label: string;
  teams: string;
  date: string;
  kickoff: string;
  endsApprox: string;
  venue: string;
}

const MATCHES = matchesData as MatchEntry[];
const NEWS_URL =
  "https://www.aljazeera.com/sports/2026/5/14/world-cup-train-and-shuttle-bus-ticket-prices-cut-in-new-york-new-jersey";
const NEWS_DATE = "2026-05-14";

const fmtDate = (iso: string, lang: Lang): string => {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const locale = lang === "es" ? "es-ES" : lang === "pt" ? "pt-BR" : "en-US";
  return dt.toLocaleDateString(locale, {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
};

export default function HomePage() {
  const [lang, setLang] = useState<Lang>("en");
  const [origin, setOrigin] = useState<OriginId | "">("");
  const [date, setDate] = useState<string>("");

  const match = useMemo(
    () => MATCHES.find((m) => m.date === date) ?? null,
    [date],
  );

  const options = useMemo(() => {
    if (!origin) return [];
    return rankOptions(origin).map((o) => ({
      ...o,
      lastReturnWarn: match ? endsLate(match.endsApprox) : false,
    }));
  }, [origin, match]);

  const originName = origin ? ORIGINS.find((o) => o.id === origin)?.name ?? "" : "";

  return (
    <div className="relative min-h-dvh">
      <div className="pointer-events-none absolute inset-0 -z-10 opacity-30 field-stripe" />
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[60vh] bg-gradient-to-b from-flame/20 via-transparent to-transparent" />

      <header className="relative mx-auto max-w-7xl px-4 pb-4 pt-6 sm:px-6 sm:pt-10">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-flame text-pitch-deep">
              <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden>
                <path
                  fill="currentColor"
                  d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm0 5 4 1.5V11c0 3.5-2.4 7-4 8.2-1.6-1.2-4-4.7-4-8.2V8.5L12 7Z"
                />
              </svg>
            </div>
            <div>
              <div className="font-display text-base font-bold tracking-tight">
                {t(lang, "brand")}
              </div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-white/50">
                MetLife Stadium · NY/NJ
              </div>
            </div>
          </div>
          <LangToggle value={lang} onChange={setLang} />
        </div>
      </header>

      <section className="relative mx-auto max-w-7xl px-4 pt-4 sm:px-6 sm:pt-10">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-7 lg:col-span-8">
            <p className="font-display text-[10px] uppercase tracking-[0.3em] text-flame">
              FIFA World Cup 26 · Match-Day Transit
            </p>
            <h1 className="mt-3 font-display text-5xl font-bold leading-[0.95] tracking-tight sm:text-6xl lg:text-7xl">
              <span className="text-chalk">Fares cut.</span>
              <br />
              <span className="bg-gradient-to-br from-flame via-gold to-electric bg-clip-text text-transparent">
                Get to MetLife
              </span>
              <span className="text-chalk"> for less.</span>
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-white/70 sm:text-lg">
              {t(lang, "tagline")} {lang === "en" && (
                <>
                  NJ Transit train is now <strong className="text-chalk">$98</strong>{" "}
                  round-trip (down from $150). Official fan shuttle is now{" "}
                  <strong className="text-chalk">$20</strong> (down from $80).
                </>
              )}
              {lang === "es" && (
                <>
                  El tren NJ Transit ahora es <strong className="text-chalk">$98</strong>{" "}
                  ida y vuelta (desde $150). El bus oficial es ahora{" "}
                  <strong className="text-chalk">$20</strong> (desde $80).
                </>
              )}
              {lang === "pt" && (
                <>
                  O trem NJ Transit agora é <strong className="text-chalk">US$98</strong>{" "}
                  ida e volta (era US$150). O ônibus oficial é{" "}
                  <strong className="text-chalk">US$20</strong> (era US$80).
                </>
              )}
            </p>
          </div>

          <aside className="col-span-12 grid grid-cols-2 gap-3 md:col-span-5 lg:col-span-4">
            <Stat
              big="$98"
              old="$150"
              label={lang === "es" ? "Tren ida y vuelta" : lang === "pt" ? "Trem (ida e volta)" : "Train round-trip"}
              accent="flame"
            />
            <Stat
              big="$20"
              old="$80"
              label={lang === "es" ? "Bus oficial" : lang === "pt" ? "Ônibus oficial" : "Official shuttle"}
              accent="electric"
            />
          </aside>
        </div>
      </section>

      <section className="relative mx-auto mt-12 max-w-7xl px-4 sm:px-6">
        <div className="card-edge grain relative overflow-hidden rounded-3xl border border-white/10 bg-pitch/60 p-6 backdrop-blur-sm sm:p-8">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <OriginPicker value={origin} onChange={setOrigin} lang={lang} />

            <fieldset className="space-y-3">
              <legend className="font-display text-xs uppercase tracking-[0.2em] text-white/60">
                {t(lang, "pickMatch")}
              </legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {MATCHES.map((m) => {
                  const active = m.date === date;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setDate(m.date)}
                      aria-pressed={active}
                      className={
                        "focus-ring rounded-2xl border p-3 text-left transition-all " +
                        (active
                          ? "border-electric bg-electric/15 text-white"
                          : "border-white/10 bg-white/[0.03] text-white/80 hover:border-white/30 hover:bg-white/[0.06]")
                      }
                    >
                      <div className="font-display text-sm font-semibold leading-tight">
                        {fmtDate(m.date, lang)}
                      </div>
                      <div className="mt-1 text-[10px] uppercase tracking-widest text-white/40">
                        {m.kickoff} · {m.label.split(" — ")[0]}
                      </div>
                    </button>
                  );
                })}
              </div>
            </fieldset>
          </div>
        </div>
      </section>

      <section className="relative mx-auto mt-12 max-w-7xl px-4 pb-16 sm:px-6">
        {options.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.02] p-12 text-center text-white/50">
            <p className="font-display text-lg">{t(lang, "selectBoth")}</p>
          </div>
        ) : (
          <>
            <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
                  {t(lang, "optionsHeading")}
                </h2>
                <p className="mt-1 text-sm text-white/50">
                  {t(lang, "resultsFor")}{" "}
                  <span className="text-white/80">{originName}</span>
                  {match && (
                    <>
                      {" "}
                      {t(lang, "on")}{" "}
                      <span className="text-white/80">
                        {fmtDate(match.date, lang)} · {match.kickoff}
                      </span>
                    </>
                  )}
                </p>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-widest text-white/60">
                {t(lang, "cheapestFirst")}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {options.map((opt, idx) => (
                <FareCard
                  key={opt.mode}
                  option={opt}
                  rank={idx + 1}
                  lang={lang}
                  match={match}
                  originName={originName}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <section
        id="faq"
        className="relative mx-auto max-w-7xl px-4 pb-20 sm:px-6"
        aria-labelledby="faq-heading"
      >
        <h2
          id="faq-heading"
          className="font-display text-2xl font-bold tracking-tight sm:text-3xl"
        >
          {t(lang, "faq")}
        </h2>
        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2">
          {(["faqQ1", "faqQ2", "faqQ3", "faqQ4"] as const).map((q, i) => (
            <details
              key={q}
              className="group card-edge rounded-2xl border border-white/10 bg-white/[0.03] p-5 open:bg-white/[0.06]"
            >
              <summary className="focus-ring flex cursor-pointer list-none items-center justify-between gap-3 font-display text-base font-semibold">
                <span>{t(lang, q)}</span>
                <span className="text-flame transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-white/70">
                {t(lang, `faqA${i + 1}`)}
              </p>
            </details>
          ))}
        </div>
      </section>

      <footer className="relative mx-auto max-w-7xl px-4 pb-10 sm:px-6">
        <div className="flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-white/50 sm:flex-row sm:items-center sm:justify-between">
          <p>{t(lang, "footerNote")}</p>
          <a
            href={NEWS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="focus-ring inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 font-semibold text-white/80 hover:text-white"
          >
            <span>📰 {t(lang, "newsSource")} · Al Jazeera</span>
            <span className="text-white/40">· {t(lang, "publishedOn")} {NEWS_DATE}</span>
          </a>
        </div>
      </footer>
    </div>
  );
}

function Stat({
  big,
  old,
  label,
  accent,
}: {
  big: string;
  old: string;
  label: string;
  accent: "flame" | "electric";
}) {
  const accentClass =
    accent === "flame"
      ? "from-flame/30 via-flame/10 border-flame/30"
      : "from-electric/30 via-electric/10 border-electric/30";
  return (
    <div
      className={
        "card-edge relative overflow-hidden rounded-2xl border bg-gradient-to-br to-transparent p-4 " +
        accentClass
      }
    >
      <div className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
        {big}
      </div>
      <div className="mt-1 text-[10px] uppercase tracking-widest text-white/60">
        {label}
      </div>
      <div className="mt-2 text-xs text-white/40 line-through">{old}</div>
    </div>
  );
}
