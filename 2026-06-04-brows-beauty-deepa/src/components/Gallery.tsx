"use client";

import { useState } from "react";
import Image from "next/image";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { ZoomIn } from "lucide-react";

const galleryItems = [
  { id: 1, alt: "Before & After: Eyebrow Threading — REPLACE WITH REAL PHOTO", color: "e8b4b4" },
  { id: 2, alt: "Before & After: Brow Tinting — REPLACE WITH REAL PHOTO", color: "d4a5a5" },
  { id: 3, alt: "Before & After: Facial Threading — REPLACE WITH REAL PHOTO", color: "c9b1b1" },
  { id: 4, alt: "Before & After: Henna Brows — REPLACE WITH REAL PHOTO", color: "e0c4c4" },
  { id: 5, alt: "Before & After: Brow Shaping — REPLACE WITH REAL PHOTO", color: "d8a0a0" },
  { id: 6, alt: "Before & After: Full Brow Makeover — REPLACE WITH REAL PHOTO", color: "c49090" },
];

export default function Gallery() {
  const [selectedImage, setSelectedImage] = useState<number | null>(null);

  return (
    <section id="gallery" className="py-16 md:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <div className="text-center">
          <h2 className="font-heading text-3xl font-bold text-foreground md:text-4xl">
            Before & After
          </h2>
          <div className="mx-auto mt-3 h-1 w-16 rounded-full bg-secondary" />
          <p className="mt-4 text-muted-foreground">
            See the transformation our clients love
          </p>
        </div>

        <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-3">
          {galleryItems.map((item) => (
            <Dialog key={item.id}>
              <DialogTrigger>
                <div className="group relative aspect-square cursor-pointer overflow-hidden rounded-xl bg-muted">
                  <Image
                    src={`https://placehold.co/600x600/${item.color}/666666?text=Photo+${item.id}`}
                    alt={item.alt}
                    fill
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors duration-300 group-hover:bg-black/30">
                    <ZoomIn className="h-8 w-8 text-white opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                  </div>
                </div>
              </DialogTrigger>
              <DialogContent className="max-w-2xl p-0">
                <Image
                  src={`https://placehold.co/800x800/${item.color}/666666?text=Photo+${item.id}`}
                  alt={item.alt}
                  width={800}
                  height={800}
                  className="w-full rounded-lg"
                />
              </DialogContent>
            </Dialog>
          ))}
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          📸 These are placeholder images. Real before & after photos coming soon!
        </p>
      </div>
    </section>
  );
}
