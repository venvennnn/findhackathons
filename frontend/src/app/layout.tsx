import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title:
    "FindHackathons — open hackathons and ML competitions, ranked by effort",
  description:
    "Live hackathons from Devpost, Kaggle and Devfolio with skill floor, eligibility and an honest weekend estimate. Describe yourself and get the nine worth entering.",
  metadataBase: new URL("https://findhackathons.com"),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
