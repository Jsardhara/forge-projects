interface SectionHeadingProps {
  title: string;
  subtitle?: string;
  light?: boolean;
}

export default function SectionHeading({ title, subtitle, light = false }: SectionHeadingProps) {
  return (
    <div className="text-center mb-12">
      <h2
        className={`text-3xl md:text-4xl font-heading font-semibold mb-3 ${
          light ? "text-white" : "text-foreground"
        }`}
      >
        {title}
      </h2>
      <div className="w-16 h-1 bg-secondary mx-auto rounded-full" />
      {subtitle && (
        <p
          className={`mt-4 text-lg max-w-2xl mx-auto ${
            light ? "text-white/80" : "text-muted-foreground"
          }`}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
