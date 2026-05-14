"use client";

import { Lang, LANGS } from "@/lib/i18n";

interface Props {
  value: Lang;
  onChange: (lang: Lang) => void;
}

export default function LangToggle({ value, onChange }: Props) {
  return (
    <div
      role="group"
      aria-label="Language"
      className="inline-flex rounded-full border border-white/10 bg-white/5 p-1 text-xs"
    >
      {LANGS.map((l) => {
        const active = l.id === value;
        return (
          <button
            key={l.id}
            type="button"
            onClick={() => onChange(l.id)}
            aria-pressed={active}
            className={
              "focus-ring rounded-full px-3 py-1 font-semibold tracking-wider transition-colors " +
              (active
                ? "bg-flame text-pitch-deep"
                : "text-white/70 hover:text-white")
            }
          >
            {l.flag}
          </button>
        );
      })}
    </div>
  );
}
