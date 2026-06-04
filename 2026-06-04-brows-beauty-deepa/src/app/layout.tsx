import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
});

export const metadata: Metadata = {
  title:
    "Brows & Beauty by Deepa | Brow Threading, Waxing & Tinting in Wyomissing, PA",
  description:
    "Expert brow threading, waxing, and tinting in Wyomissing, PA. Personalized beauty services by Deepa. Trusted by 2,900+ happy clients. Book your appointment today.",
  keywords: [
    "brow threading",
    "eyebrow tinting",
    "facial waxing",
    "facial threading",
    "henna brows",
    "lash tint",
    "Wyomissing PA",
    "Reading PA",
    "beauty salon",
    "brow specialist",
  ],
  openGraph: {
    title: "Brows & Beauty by Deepa | Brow Threading & Waxing in Wyomissing, PA",
    description:
      "Expert brow threading, waxing, and tinting in Wyomissing, PA. Trusted by 2,900+ happy clients.",
    type: "website",
    locale: "en_US",
    siteName: "Brows & Beauty by Deepa",
  },
  twitter: {
    card: "summary_large_image",
    title: "Brows & Beauty by Deepa",
    description:
      "Expert brow threading, waxing, and tinting in Wyomissing, PA.",
  },
  alternates: {
    canonical: "https://browsandbeautybydeepa.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${playfair.variable}`}>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "BeautySalon",
              name: "Brows & Beauty by Deepa",
              description:
                "Expert brow threading, waxing, and tinting in Wyomissing, PA",
              address: {
                "@type": "PostalAddress",
                addressLocality: "Wyomissing",
                addressRegion: "PA",
                addressCountry: "US",
              },
              telephone: "(XXX) XXX-XXXX",
              openingHoursSpecification: [
                {
                  "@type": "OpeningHoursSpecification",
                  dayOfWeek: [
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                  ],
                  opens: "10:00",
                  closes: "18:00",
                },
              ],
              priceRange: "$$",
              url: "https://browsandbeautybydeepa.com",
              sameAs: [
                "https://www.facebook.com/BrowsandBeautybyDeepa/",
              ],
            }),
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
