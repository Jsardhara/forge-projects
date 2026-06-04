"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Phone, Clock, MapPin } from "lucide-react";

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

export default function Contact() {
  return (
    <section id="contact" className="py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
            Book Your Appointment
          </h2>
          <div className="mx-auto mt-3 h-1 w-16 rounded-full bg-secondary" />
          <p className="mt-4 text-muted-foreground">
            Call, message, or fill out the form below
          </p>
        </div>

        <div className="mt-12 grid gap-12 md:grid-cols-2">
          {/* Contact Info */}
          <div className="space-y-8">
            <div>
              <h3 className="font-heading text-xl font-semibold text-foreground">
                Get in Touch
              </h3>
              <p className="mt-2 text-muted-foreground">
                The easiest way to book is to call or text directly. You can also
                send a message through the form or on Facebook.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Phone className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Phone</p>
                  <p className="text-muted-foreground">(XXX) XXX-XXXX</p>
                  <p className="text-xs text-muted-foreground">
                    📞 Replace with real number
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Hours</p>
                  <p className="text-muted-foreground">
                    Tuesday – Saturday: 10AM – 6PM
                  </p>
                  <p className="text-muted-foreground">
                    Sunday – Monday: Closed
                  </p>
                  <p className="text-xs text-muted-foreground">
                    ⏰ Confirm with Deepa
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <MapPin className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Location</p>
                  <p className="text-muted-foreground">Wyomissing, PA</p>
                  <p className="text-xs text-muted-foreground">
                    📍 Full address coming soon
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FacebookIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium text-foreground">Facebook</p>
                  <a
                    href="https://www.facebook.com/BrowsandBeautybyDeepa/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline underline-offset-2 hover:text-primary/80"
                  >
                    Brows & Beauty by Deepa
                  </a>
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-gradient-to-br from-primary/10 to-secondary/10 p-6">
              <p className="font-heading text-lg font-semibold text-foreground">
                Ready for your perfect brows?
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Call or text Deepa directly to book your appointment. Walk-ins
                welcome based on availability.
              </p>
              <Button className="mt-4 bg-secondary text-secondary-foreground hover:bg-secondary/90">
                <Phone className="mr-2 h-4 w-4" />
                Call Now
              </Button>
            </div>
          </div>

          {/* Contact Form */}
          <div>
            <Card className="border-border">
              <CardContent className="p-6">
                <h3 className="font-heading text-lg font-semibold text-foreground">
                  Send a Message
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Deepa will get back to you within 24 hours
                </p>
                <form
                  action="https://formspree.io/f/xpwdqjkl"
                  method="POST"
                  className="mt-6 space-y-4"
                >
                  <div>
                    <label
                      htmlFor="name"
                      className="mb-1 block text-sm font-medium text-foreground"
                    >
                      Name
                    </label>
                    <Input
                      id="name"
                      name="name"
                      placeholder="Your name"
                      required
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="phone"
                      className="mb-1 block text-sm font-medium text-foreground"
                    >
                      Phone
                    </label>
                    <Input
                      id="phone"
                      name="phone"
                      type="tel"
                      placeholder="(XXX) XXX-XXXX"
                      required
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="service"
                      className="mb-1 block text-sm font-medium text-foreground"
                    >
                      Service Interested In
                    </label>
                    <select
                      id="service"
                      name="service"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">Select a service</option>
                      <option value="threading">Eyebrow Threading</option>
                      <option value="tinting">Brow Tinting</option>
                      <option value="facial-threading">Facial Threading</option>
                      <option value="waxing">Facial Waxing</option>
                      <option value="henna">Henna Brows</option>
                      <option value="lash-tint">Lash Tint</option>
                      <option value="other">Other / Not Sure</option>
                    </select>
                  </div>
                  <div>
                    <label
                      htmlFor="message"
                      className="mb-1 block text-sm font-medium text-foreground"
                    >
                      Message
                    </label>
                    <Textarea
                      id="message"
                      name="message"
                      placeholder="Tell us what you're looking for..."
                      rows={4}
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Send Message
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}

