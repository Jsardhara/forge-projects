import Link from "next/link";

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="border-t border-border bg-foreground text-background">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-3">
          {/* Brand */}
          <div>
            <h3 className="font-heading text-lg font-bold text-white">
              Brows & Beauty by Deepa
            </h3>
            <p className="mt-2 text-sm text-white/60">
              Expert brow threading, waxing, and tinting in Wyomissing, PA.
              Trusted by 2,900+ happy clients.
            </p>
            <div className="mt-4 flex gap-3">
              <a
                href="https://www.facebook.com/BrowsandBeautybyDeepa/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white/70 transition-colors hover:bg-white/20 hover:text-white"
                aria-label="Facebook"
              >
                <FacebookIcon className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold text-white">Quick Links</h4>
            <ul className="mt-3 space-y-2">
              {[
                { href: "#services", label: "Services" },
                { href: "#about", label: "About" },
                { href: "#gallery", label: "Gallery" },
                { href: "#reviews", label: "Reviews" },
                { href: "#contact", label: "Contact" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-white/60 transition-colors hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Hours */}
          <div>
            <h4 className="font-semibold text-white">Hours</h4>
            <ul className="mt-3 space-y-1 text-sm text-white/60">
              <li>Tuesday – Saturday</li>
              <li className="pl-4">10:00 AM – 6:00 PM</li>
              <li className="mt-2">Sunday – Monday</li>
              <li className="pl-4">Closed</li>
            </ul>
            <p className="mt-3 text-xs text-white/40">
              Hours may vary. Call to confirm.
            </p>
          </div>
        </div>

        <div className="mt-10 border-t border-white/10 pt-6 text-center text-xs text-white/40">
          <p>
            © {new Date().getFullYear()} Brows & Beauty by Deepa. All rights
            reserved.
          </p>
          <p className="mt-1">
            Wyomissing, PA · (XXX) XXX-XXXX
          </p>
        </div>
      </div>
    </footer>
  );
}
