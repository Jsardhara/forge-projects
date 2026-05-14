import { Lang, t } from "@/lib/i18n";

export default function LastReturnBadge({ lang }: { lang: Lang }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-gold/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-gold">
      <svg viewBox="0 0 16 16" className="h-3 w-3" aria-hidden>
        <path
          fill="currentColor"
          d="M8 1.5 0.5 14.5h15L8 1.5Zm0 4.5 5 8H3l5-8Zm-.75 2v3h1.5V8h-1.5Zm0 4v1.25h1.5V12h-1.5Z"
        />
      </svg>
      {t(lang, "lastReturnWarn")}
    </span>
  );
}
