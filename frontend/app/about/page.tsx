import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
};

export default function AboutPage() {
  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-neutral-950 text-neutral-100 px-6 py-12 text-center">
      <h1 className="font-heading text-3xl mb-6">About LayScience</h1>
      <p className="max-w-prose mb-4">
        LayScience is an AI tool that turns research papers (PDF, DOI, or URL) into clear, trustworthy plain-language summaries—either ultra-short “micro-stories” or more detailed write-ups. Built first with and for Kabul University’s female students—who face one of the world’s most challenging educational environments—it’s also for anyone who finds papers long, technical, or hard to follow. The goal is to spark curiosity and make open science genuinely accessible.
      </p>
      <p className="max-w-prose">
        You can run up to five summaries without an account; for more, please create a free account. If you’re able, consider chipping in to help cover hosting and API costs so the service stays available to people who can’t afford much. Created by Rashid Mushkani, © 2025. All rights reserved.
      </p>
      <p className="max-w-prose mt-4">
        Contact me at
        <a href="mailto:rashidmushkani@gmail.com" className="underline ml-1">
          rashidmushkani@gmail.com 
        </a>
        for questions or feedback.
      </p>
    </main>
  );
}
