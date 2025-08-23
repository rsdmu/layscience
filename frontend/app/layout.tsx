import "./globals.css";
import type { Metadata, Viewport } from "next";
import ClientToaster from "@/components/ClientToaster";
import { Bebas_Neue, Inter } from "next/font/google";

const heading = Bebas_Neue({ weight: "400", subsets: ["latin"], variable: "--font-heading" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://layscience.onrender.com";

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: "Lay Science",
    template: "%s | Lay Science",
  },
  description: "AI that turns research into clear, engaging summaries.",
  icons: { icon: "/icon.png" },
  alternates: { canonical: "/" },
  openGraph: {
    title: "Lay Science",
    description: "AI that turns research into clear, engaging summaries.",
    url: baseUrl,
    siteName: "Lay Science",
    images: [{ url: "/icon.png", width: 96, height: 96 }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Lay Science",
    description: "AI that turns research into clear, engaging summaries.",
    images: ["/icon.png"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${heading.variable} ${body.variable}`}>
      <body>
        {children}
        <p className="fixed bottom-0 left-0 w-full pb-2 text-center text-xs text-neutral-400">
          AI can make mistakes. LayScience is still in test.
        </p>
        <ClientToaster />
      </body>
    </html>
  );
}
