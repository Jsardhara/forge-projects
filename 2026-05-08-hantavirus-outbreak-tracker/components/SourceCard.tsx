type Props = {
  href: string;
  label: string;
  title: string;
  blurb: string;
};

export default function SourceCard({ href, label, title, blurb }: Props) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="block border border-ink/10 rounded-lg p-4 bg-white/40 hover:border-rust transition-colors"
    >
      <div className="text-xs uppercase tracking-widest text-rust font-semibold">{label}</div>
      <div className="font-serif text-lg font-bold mt-1">{title}</div>
      <p className="text-sm text-ink/70 mt-1">{blurb}</p>
      <div className="text-xs text-ink/50 mt-2">Open ↗</div>
    </a>
  );
}
