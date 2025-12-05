import "./globals.css";
import type { Metadata, Viewport } from "next";
import ClientToaster from "@/components/ClientToaster";
import AboutHomeLink from "@/components/AboutHomeLink";
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
  icons: {
    icon: [{ url: "/cocoon/static/cocoon-logo-blue.png", type: "image/png", sizes: "512x512" }],
    apple: "/cocoon/static/cocoon-logo-blue.png",
    shortcut: "/cocoon/static/cocoon-logo-blue.png",
  },
  alternates: { canonical: "/" },
  openGraph: {
    title: "Lay Science",
    description: "AI that turns research into clear, engaging summaries.",
    url: baseUrl,
    siteName: "Lay Science",
    images: [{ url: "/cocoon/static/cocoon-logo-blue.png", width: 512, height: 512 }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Lay Science",
    description: "AI that turns research into clear, engaging summaries.",
    images: ["/cocoon/static/cocoon-logo-blue.png"],
  },
  manifest: "/site.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
      <html lang="en" className={`${heading.variable} ${body.variable}`}>
        <body>
          <AboutHomeLink />
          {children}
          <ClientToaster />
        </body>
      </html>
  );
}
