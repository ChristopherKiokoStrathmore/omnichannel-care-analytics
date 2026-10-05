import type { Metadata, Viewport } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const sans = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Omnichannel care analytics",
    template: "%s · Omnichannel care analytics",
  },
  description:
    "SYNTHETIC journey KPI demo, seed 20260929. Resolution rate 81.4% (3256/4000). Digital-first journeys that later reach a call: 32.0% (971/3035).",
};

export const viewport: Viewport = {
  themeColor: "#efece4",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body>
        <a className="skip" href="#content">
          Skip to content
        </a>
        <SiteHeader />
        <SyntheticBanner />
        <main id="content">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
