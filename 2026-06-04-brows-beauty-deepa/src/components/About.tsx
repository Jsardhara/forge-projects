import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

export default function About() {
  return (
    <section id="about" className="bg-muted/50 py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="grid items-center gap-12 md:grid-cols-2">
          {/* Photo */}
          <div className="flex justify-center">
            <div className="relative">
              <div className="absolute -inset-4 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 blur-xl" />
              <Avatar className="relative h-64 w-64 border-4 border-background shadow-xl md:h-80 md:w-80">
                <AvatarFallback className="bg-gradient-to-br from-primary to-accent font-heading text-6xl font-bold text-white">
                  D
                </AvatarFallback>
              </Avatar>
            </div>
          </div>

          {/* Bio */}
          <div>
            <Badge variant="secondary" className="mb-4">
              Meet Your Specialist
            </Badge>
            <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
              Meet Deepa
            </h2>
            <div className="mt-3 h-1 w-16 rounded-full bg-secondary" />
            <div className="mt-6 space-y-4 text-muted-foreground leading-relaxed">
              <p>
                Deepa is a certified brow specialist and beauty artist serving
                Wyomissing and the greater Reading, PA area. With years of
                experience in precision threading, waxing, and brow tinting,
                she&apos;s helped over 2,900 clients look and feel their best.
              </p>
              <p>
                Her approach combines technical skill with a personal touch —
                every client leaves feeling confident and cared for. Deepa takes
                the time to understand your unique face shape and style
                preferences to deliver brows that truly frame your features.
              </p>
              <p>
                When she&apos;s not perfecting brows, Deepa stays on top of the
                latest beauty trends and techniques to bring her clients the
                best possible experience. Her warm, welcoming demeanor has made
                her a trusted name in the local beauty community.
              </p>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <Badge variant="outline">Certified Specialist</Badge>
              <Badge variant="outline">2,900+ Clients</Badge>
              <Badge variant="outline">Threading Expert</Badge>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
