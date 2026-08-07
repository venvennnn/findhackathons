import type { Metadata } from "next";
import { DM_Sans, Syne } from "next/font/google";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["600", "700", "800"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "FindHackathons — Finishable competitions, matched to you",
  description:
    "AI-enriched discovery for developer hackathons and data science competitions. Beginner-first matches with clear eligibility, deadlines, and starter-code signals.",
  metadataBase: new URL("https://findhackathons.com"),
  openGraph: {
    title: "FindHackathons",
    description:
      "Go from landing page to 3–5 finishable hackathons in under 90 seconds.",
    url: "https://findhackathons.com",
    siteName: "FindHackathons",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${syne.variable} ${dmSans.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}