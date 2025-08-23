import "./globals.css";
import type { Metadata, Viewport } from "next";
import ClientToaster from "@/components/ClientToaster";
import { Bebas_Neue, Inter } from "next/font/google";

const heading = Bebas_Neue({ weight: "400", subsets: ["latin"], variable: "--font-heading" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Lay Science",
  description: "AI that turns research into clear, engaging summaries.",
  icons: { icon: "/icon.png" },
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
