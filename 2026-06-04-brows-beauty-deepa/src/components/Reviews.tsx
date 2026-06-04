import { Card, CardContent } from "@/components/ui/card";
import { Star } from "lucide-react";

const reviews = [
  {
    name: "Sarah M.",
    text: "Deepa is the best! My brows have never looked so clean and shaped perfectly. I've been coming back for a year now and I wouldn't go anywhere else.",
  },
  {
    name: "Jessica L.",
    text: "The threading is so precise and barely hurts compared to waxing. I'm a client for life!",
  },
  {
    name: "Priya K.",
    text: "Finally found someone who knows how to shape South Asian brows properly. Deepa really understands different face shapes and brow types.",
  },
  {
    name: "Maria R.",
    text: "I got my brows tinted for the first time and I'm obsessed. Looks so natural but makes such a difference. Thank you Deepa!",
  },
  {
    name: "Amanda T.",
    text: "Such a warm, welcoming experience. Deepa takes her time and always makes sure I'm happy with the result. Highly recommend!",
  },
  {
    name: "Nicole W.",
    text: "Been going to Deepa for threading and waxing for 2 years. Professional, hygienic, and always consistent. My go-to brow lady!",
  },
];

function Stars() {
  return (
    <div className="flex gap-0.5">
      {[...Array(5)].map((_, i) => (
        <Star
          key={i}
          className="h-4 w-4 fill-secondary text-secondary"
        />
      ))}
    </div>
  );
}

export default function Reviews() {
  return (
    <section id="reviews" className="bg-muted/50 py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
            What Our Clients Say
          </h2>
          <div className="mx-auto mt-3 h-1 w-16 rounded-full bg-secondary" />
          <p className="mt-4 text-muted-foreground">
            Trusted by 2,900+ happy clients in the Reading area
          </p>
        </div>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {reviews.map((review) => (
            <Card key={review.name} className="border-border">
              <CardContent className="p-6">
                <Stars />
                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                  &ldquo;{review.text}&rdquo;
                </p>
                <p className="mt-4 text-sm font-semibold text-foreground">
                  — {review.name}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
