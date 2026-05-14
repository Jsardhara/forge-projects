import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WC26 Fare Finder — NY/NJ Match-Day Transit",
  description:
    "Compare NJ Transit, official shuttle bus, PATH, rideshare and drive+park for MetLife Stadium on FIFA World Cup 2026 match days. Built off the May 2026 NY/NJ fare cuts.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
