import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary via-accent to-primary/80">
      {/* Decorative overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.15),transparent_50%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(255,255,255,0.1),transparent_50%)]" />

      <div className="relative mx-auto max-w-6xl px-4 py-24 text-center md:py-36">
        <p className="animate-fade-in-up mb-4 text-sm font-medium uppercase tracking-widest text-white/70">
          Wyomissing, PA
        </p>
        <h1 className="animate-fade-in-up animate-delay-100 font-heading text-4xl font-bold text-white md:text-5xl lg:text-6xl">
          Expert Brow Threading,
          <br />
          Waxing & Tinting
        </h1>
        <p className="animate-fade-in-up animate-delay-200 mx-auto mt-6 max-w-2xl text-lg text-white/80 md:text-xl">
          Personalized beauty services by Deepa — trusted by 2,900+ happy
          clients in the Reading, PA area
        </p>
        <div className="animate-fade-in-up animate-delay-300 mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button
            size="lg"
            className="bg-secondary text-secondary-foreground hover:bg-secondary/90 px-8 text-base font-semibold shadow-lg"
          >
            Book Now
          </Button>
          <Link
            href="#services"
            className="inline-flex h-11 items-center justify-center rounded-md border border-white/30 bg-white/10 px-8 text-base font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/20"
          >
            View Services
          </Link>
        </div>
      </div>

      {/* Bottom wave */}
      <div className="absolute bottom-0 left-0 right-0">
        <svg viewBox="0 0 1440 80" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
          <path d="M0 80V40C240 0 480 0 720 20C960 40 1200 60 1440 40V80H0Z" fill="var(--background)" />
        </svg>
      </div>
    </section>
  );
}
