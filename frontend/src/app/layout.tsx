import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FindHackathons",
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
      <body>{children}</body>
    </html>
  );
}
