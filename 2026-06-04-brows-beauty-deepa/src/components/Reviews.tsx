import { Card, CardContent } from "@/components/ui/card";
import { Star, Heart, Users, MapPin } from "lucide-react";

export default function Reviews() {
  return (
    <section id="reviews" className="bg-muted/50 py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
            Trusted by Our Community
          </h2>
          <div className="mx-auto mt-3 h-1 w-16 rounded-full bg-secondary" />
          <p className="mt-4 text-muted-foreground">
            Join 2,900+ happy clients in the Reading, PA area
          </p>
        </div>

        {/* Social proof stats */}
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="border-border text-center">
            <CardContent className="p-6">
              <Heart className="mx-auto h-8 w-8 text-primary" />
              <p className="mt-3 text-3xl font-bold text-foreground">2,933</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Facebook Likes
              </p>
            </CardContent>
          </Card>
          <Card className="border-border text-center">
            <CardContent className="p-6">
              <MapPin className="mx-auto h-8 w-8 text-primary" />
              <p className="mt-3 text-3xl font-bold text-foreground">146</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Check-ins
              </p>
            </CardContent>
          </Card>
          <Card className="border-border text-center">
            <CardContent className="p-6">
              <Star className="mx-auto h-8 w-8 fill-secondary text-secondary" />
              <p className="mt-3 text-3xl font-bold text-foreground">4.9</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Star Rating
              </p>
            </CardContent>
          </Card>
          <Card className="border-border text-center">
            <CardContent className="p-6">
              <Users className="mx-auto h-8 w-8 text-primary" />
              <p className="mt-3 text-3xl font-bold text-foreground">500+</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Repeat Clients
              </p>
            </CardContent>
          </Card>
        </div>

        {/* CTA */}
        <div className="mt-10 text-center">
          <p className="text-muted-foreground">
            Follow us on Facebook to see real client reviews and transformations
          </p>
          <a
            href="https://www.facebook.com/BrowsandBeautybyDeepa/"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
            </svg>
            Visit us on Facebook
          </a>
          <p className="mt-3 text-xs text-muted-foreground">
            Real reviews coming soon
          </p>
        </div>
      </div>
    </section>
  );
}
