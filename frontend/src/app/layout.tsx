import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FindHackathons — hackathons you can actually finish",
  description:
    "Active hackathons and data science competitions — Devpost, Kaggle, Devfolio, and more.",
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
