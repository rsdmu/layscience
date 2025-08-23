"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import toast from "react-hot-toast";
import type { Metadata } from "next";
import { registerAccount, verifyCode } from "@/lib/api";

console.info("API base", process.env.NEXT_PUBLIC_API_BASE);

export const metadata: Metadata = {
  title: "Welcome",
  description:
    "Create an account or test Lay Science—the AI that turns research into clear, engaging summaries.",
};

export default function Welcome() {
  const [step, setStep] = useState<"choice" | "register" | "verify">("choice");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");

  async function onRegister() {
    try {
      await registerAccount({ username, email });
      toast.success("Verification code sent");
      setStep("verify");
    } catch (e: any) {
      toast.error(e.message || "Failed to send code");
    }
  }

  async function onVerify() {
    try {
      await verifyCode({ email, code });
      localStorage.setItem("hasAccount", "true");
      toast.success("Account verified");
      setStep("choice");
    } catch (e: any) {
      toast.error(e.message || "Verification failed");
    }
  }

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-neutral-950 text-neutral-100 px-6 text-center">
      <Image src="/icon.png" alt="Lay Science logo" width={96} height={96} className="mb-4 opacity-80" />
      <h1 className="font-heading text-4xl mb-6">Lay Science</h1>

      {step === "choice" && (
        <div className="space-y-4 w-full max-w-xs">
          <button
            className="w-full rounded bg-white/10 hover:bg-white/20 py-2"
            onClick={() => setStep("register")}
          >
            Create account
          </button>
          <Link
            href="/summarize"
            className="block w-full rounded border border-white/10 py-2 hover:bg-white/5"
          >
            Test without account
          </Link>
        </div>
      )}

      {step === "register" && (
        <div className="space-y-4 w-full max-w-xs">
          <input
            className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <p className="text-sm text-neutral-400">
            Lay Science is free for personal use. Contact us for commercial licensing.
          </p>
          <button
            className="w-full rounded bg-white/10 hover:bg-white/20 py-2"
            onClick={onRegister}
          >
            Send verification
          </button>
        </div>
      )}

      {step === "verify" && (
        <div className="space-y-4 w-full max-w-xs">
          <input
            className="w-full rounded bg-neutral-900 border border-neutral-700 px-3 py-2"
            placeholder="Verification code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button
            className="w-full rounded bg-white/10 hover:bg-white/20 py-2"
            onClick={onVerify}
          >
            Verify
          </button>
        </div>
      )}
    </main>
  );
}
