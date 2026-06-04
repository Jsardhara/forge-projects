import { Card, CardContent } from "@/components/ui/card";
import { Scissors, Sparkles, Eye, Flower2, Palette, Laugh } from "lucide-react";

const services = [
  {
    icon: Scissors,
    name: "Eyebrow Threading",
    description:
      "Precise shaping with thread technique for clean, defined brows that frame your face perfectly.",
    price: "$15–25",
  },
  {
    icon: Eye,
    name: "Brow Tinting",
    description:
      "Semi-permanent color for fuller, darker brows that last for weeks.",
    price: "$20–30",
  },
  {
    icon: Sparkles,
    name: "Facial Threading",
    description:
      "Gentle, precise hair removal for lip, chin, and full face.",
    price: "$15–45",
  },
  {
    icon: Flower2,
    name: "Facial Waxing",
    description:
      "Quick, effective hair removal for smooth, lasting results.",
    price: "$12–50",
  },
  {
    icon: Palette,
    name: "Henna Brows",
    description:
      "Natural henna tint for bold, beautiful brows with a soft stain.",
    price: "$35–50",
  },
  {
    icon: Laugh,
    name: "Lash Tint",
    description:
      "Darken your lashes naturally — no mascara needed for weeks.",
    price: "$25–35",
  },
];

export default function Services() {
  return (
    <section id="services" className="py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
            Our Services
          </h2>
          <div className="mx-auto mt-3 h-1 w-16 rounded-full bg-secondary" />
          <p className="mt-4 text-muted-foreground">
            Expert beauty services tailored to you
          </p>
        </div>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((service) => (
            <Card
              key={service.name}
              className="group border-border transition-all duration-200 hover:shadow-lg hover:border-primary/30"
            >
              <CardContent className="p-6">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <service.icon className="h-6 w-6" />
                </div>
                <h3 className="font-heading text-lg font-semibold text-foreground">
                  {service.name}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {service.description}
                </p>
                <p className="mt-4 text-sm font-semibold text-primary">
                  {service.price}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
