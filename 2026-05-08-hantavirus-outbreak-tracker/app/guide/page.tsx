import SourceCard from '../../components/SourceCard';

export const metadata = { title: 'What to do if exposed — Hantavirus Tracker' };

export default function GuidePage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10 md:py-14">
      <p className="text-xs uppercase tracking-widest text-rust font-semibold mb-2">Action guide</p>
      <h1 className="font-serif text-3xl md:text-4xl font-bold leading-tight">
        What to do if you think you've been exposed
      </h1>
      <p className="mt-3 text-ink/70">
        Plain-language steps. Read top to bottom. Do the relevant ones.
      </p>

      <Section title="1. If you have severe symptoms — call emergency services now">
        <p>
          Severe shortness of breath, chest tightness, or feeling like you can't get enough air —
          call <strong>999 (UK)</strong>, <strong>112 (EU)</strong>, or <strong>911 (US)</strong>.
          Hantavirus pulmonary syndrome can deteriorate within hours and benefits from early
          intensive care.
        </p>
      </Section>

      <Section title="2. If you have flu-like symptoms with possible exposure">
        <ul className="list-disc list-inside space-y-2">
          <li>Contact your GP, NHS 111, or local urgent care today.</li>
          <li>Tell them about cruise ship travel, port visits, or rodent contact.</li>
          <li>Ask specifically about hantavirus serology and PCR testing.</li>
          <li>Avoid NSAIDs (ibuprofen, naproxen) until kidney involvement is ruled out.</li>
          <li>Stay hydrated. Track temperature and breathing every 4 hours.</li>
        </ul>
      </Section>

      <Section title="3. What to tell the clinician">
        <blockquote className="border-l-4 border-rust pl-4 italic text-ink/80">
          "I may have been exposed to hantavirus on the MV Atlantic Voyager voyage between 28 April
          and 12 May 2026 (or via close contact with a passenger). My symptoms began on
          [DATE]. They include [LIST]. Please consider hantavirus testing —
          serology, RT-PCR, plus baseline CBC, CMP, LDH, and chest imaging — and notify public
          health."
        </blockquote>
        <p className="mt-3 text-sm text-ink/70">
          Differential diagnoses to mention: leptospirosis, dengue, Lassa fever, severe influenza.
        </p>
      </Section>

      <Section title="4. HPS vs HFRS — quick reference">
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="border border-ink/10 rounded p-4">
            <h3 className="font-serif font-bold">HPS — pulmonary syndrome</h3>
            <p className="text-sm mt-2">
              New World hantaviruses (Sin Nombre, Andes). Lung-focused. Mortality ~36%. Watch for:
              cough, dyspnea, dropping O₂ sat, hemoconcentration on labs.
            </p>
          </div>
          <div className="border border-ink/10 rounded p-4">
            <h3 className="font-serif font-bold">HFRS — hemorrhagic + renal</h3>
            <p className="text-sm mt-2">
              Old World hantaviruses (Hantaan, Puumala, Seoul). Kidney-focused. Watch for: oliguria,
              petechiae, blurred vision, low platelets, proteinuria.
            </p>
          </div>
        </div>
      </Section>

      <Section title="5. While you wait for evaluation">
        <ul className="list-disc list-inside space-y-1">
          <li>Sleep apart from household members where practical.</li>
          <li>Wear a well-fitted mask if coughing; close-quarters spread is rare but reported.</li>
          <li>Don't cook or care for vulnerable people if febrile.</li>
          <li>Don't travel further unless to seek care.</li>
        </ul>
      </Section>

      <Section title="6. Authoritative sources">
        <div className="grid sm:grid-cols-2 gap-3">
          <SourceCard
            href="https://www.cdc.gov/hantavirus/"
            label="CDC"
            title="Hantavirus — Centers for Disease Control"
            blurb="Symptoms, transmission, treatment, prevention. Definitive US reference."
          />
          <SourceCard
            href="https://www.who.int/news-room/fact-sheets/detail/hantavirus-disease"
            label="WHO"
            title="Hantavirus — World Health Organization"
            blurb="Global epidemiology, outbreak alerts, case definitions."
          />
          <SourceCard
            href="https://www.gov.uk/government/organisations/uk-health-security-agency"
            label="UKHSA"
            title="UK Health Security Agency"
            blurb="UK contact-tracing for returning travelers from MV Atlantic Voyager."
          />
          <SourceCard
            href="https://www.aljazeera.com/news/2026/5/8/hantavirus-cases-rise-on-cruise-ship-as-uk-tracks-nationals"
            label="News"
            title="Al Jazeera — outbreak coverage, 8 May 2026"
            blurb="The reporting that triggered this tracker. Cross-reference with health authorities."
          />
        </div>
      </Section>

      <div className="mt-12 border border-ink/20 bg-ink/5 rounded-lg p-5 text-sm">
        <strong>Disclaimer.</strong> This page is informational and does not constitute medical
        advice. Decisions about your care should be made with a qualified clinician. We do not
        store your inputs; everything runs in your browser.
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="font-serif text-2xl font-bold mb-3">{title}</h2>
      <div className="text-ink/85 leading-relaxed">{children}</div>
    </section>
  );
}
