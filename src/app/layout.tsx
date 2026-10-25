import type { Metadata } from "next";
import { Cinzel, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const cinzel = Cinzel({
  variable: "--font-cinzel",
  subsets: ["latin"],
  weight: "600",
});

export const metadata: Metadata = {
  title: "Penned or Prompted? · Hybrid AI-Text Detector",
  description:
    "Paste an academic text and get the probability it is fully AI-generated, scored by a hybrid spaCy, ELECTRA and XGBoost model.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${cinzel.variable} antialiased`}>
      <body>{children}</body>
    </html>
  );
}
