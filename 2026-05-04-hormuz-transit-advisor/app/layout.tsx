import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hormuz Transit Advisor",
  description:
    "Single-page situational dashboard for the Strait of Hormuz. Risk gauge, incident timeline, escort windows, suspended operators.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 text-bone-50 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
