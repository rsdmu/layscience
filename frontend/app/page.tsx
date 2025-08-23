"use client";

import Image from "next/image";
import Link from "next/link";

export default function Welcome() {
  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-neutral-950 text-neutral-100 px-6 text-center">
      <Image
        src="/icon.png"
        alt="Lay Science logo"
        width={96}
        height={96}
        className="mb-4 opacity-80"
      />
      <h1 className="font-heading text-4xl mb-6">Lay Science</h1>
      <div className="space-y-4 w-full max-w-xs">
        <Link
          href="/register"
          className="block w-full rounded bg-white/10 hover:bg-white/20 py-2"
        >
          Create account
        </Link>
        <Link
          href="/summarize"
          className="block w-full rounded border border-white/10 py-2 hover:bg-white/5"
        >
          Test without account
        </Link>
      </div>
    </main>
  );
}

