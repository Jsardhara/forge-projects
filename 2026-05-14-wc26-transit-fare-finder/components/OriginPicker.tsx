"use client";

import { Origin, OriginId, ORIGINS } from "@/lib/routes";
import { Lang, t } from "@/lib/i18n";

interface Props {
  value: OriginId | "";
  onChange: (id: OriginId) => void;
  lang: Lang;
}

export default function OriginPicker({ value, onChange, lang }: Props) {
  return (
    <fieldset className="space-y-3">
      <legend className="font-display text-xs uppercase tracking-[0.2em] text-white/60">
        {t(lang, "pickOrigin")}
      </legend>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {ORIGINS.map((o: Origin) => {
          const active = value === o.id;
          return (
            <button
              key={o.id}
              type="button"
              onClick={() => onChange(o.id)}
              aria-pressed={active}
              className={
                "focus-ring group relative overflow-hidden rounded-2xl border p-3 text-left transition-all " +
                (active
                  ? "border-flame bg-flame/15 text-white"
                  : "border-white/10 bg-white/[0.03] text-white/80 hover:border-white/30 hover:bg-white/[0.06]")
              }
            >
              <div className="font-display text-sm font-semibold leading-tight">
                {o.name}
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-widest text-white/40">
                {o.hint}
              </div>
              {active && (
                <span
                  aria-hidden
                  className="absolute right-3 top-3 inline-block h-2 w-2 rounded-full bg-flame"
                />
              )}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
