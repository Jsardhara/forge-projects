import SymptomFlow from '../../components/SymptomFlow';
import ExposureCheck from '../../components/ExposureCheck';

export const metadata = { title: 'Symptom & Exposure Check — Hantavirus Tracker' };

export default function CheckerPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-10 md:py-14">
      <p className="text-xs uppercase tracking-widest text-rust font-semibold mb-2">Step 1 of 2</p>
      <h1 className="font-serif text-3xl md:text-4xl font-bold leading-tight">
        Quick check: do your symptoms match?
      </h1>
      <p className="mt-3 text-ink/70">
        Four questions. We don't store your answers. This is informational only — not a diagnosis.
      </p>

      <div className="mt-8 border border-ink/10 rounded-lg p-6 bg-white/40">
        <SymptomFlow />
      </div>

      <div className="mt-12">
        <p className="text-xs uppercase tracking-widest text-rust font-semibold mb-2">Step 2 of 2</p>
        <h2 className="font-serif text-2xl md:text-3xl font-bold leading-tight">
          Were you on an affected ship?
        </h2>
        <p className="mt-2 text-ink/70 text-sm">
          Enter your dates of travel to see whether they overlap with a flagged voyage.
        </p>
        <div className="mt-6 border border-ink/10 rounded-lg p-6 bg-white/40">
          <ExposureCheck />
        </div>
      </div>
    </div>
  );
}
