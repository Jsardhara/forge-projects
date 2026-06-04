"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Menu, Phone } from "lucide-react";

const navLinks = [
  { href: "#services", label: "Services" },
  { href: "#about", label: "About" },
  { href: "#gallery", label: "Gallery" },
  { href: "#reviews", label: "Reviews" },
  { href: "#contact", label: "Contact" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <span className="font-heading text-xl font-bold text-primary">
            Brows & Beauty
          </span>
          <span className="text-sm text-muted-foreground">by Deepa</span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden items-center gap-6 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-foreground transition-colors hover:text-primary"
            >
              {link.label}
            </Link>
          ))}
          <Button size="sm" className="bg-secondary text-secondary-foreground hover:bg-secondary/90">
            <Phone className="mr-2 h-4 w-4" />
            Book Now
          </Button>
        </div>

        {/* Mobile Nav */}
        <div className="flex items-center gap-2 md:hidden">
          <Button size="sm" variant="ghost" className="text-primary">
            <Phone className="h-4 w-4" />
          </Button>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger>
              <Button variant="ghost" size="icon">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-64">
              <div className="mt-8 flex flex-col gap-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="text-lg font-medium text-foreground transition-colors hover:text-primary"
                  >
                    {link.label}
                  </Link>
                ))}
                <div className="mt-4 border-t border-border pt-4">
                  <Button className="w-full bg-secondary text-secondary-foreground hover:bg-secondary/90">
                    <Phone className="mr-2 h-4 w-4" />
                    Book Now
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}
