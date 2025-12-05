"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import toast from "react-hot-toast";
import { registerAccount, verifyCode } from "@/lib/api";

export default function Welcome() {
  const [step, setStep] = useState<"choice" | "register" | "verify">("choice");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem("hasAccount") === "true") {
      router.replace("/summarize");
    }
  }, [router]);

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
      localStorage.setItem("username", username);
      localStorage.setItem("email", email);
      toast.success("Account verified");
      router.push("/summarize");
    } catch (e: any) {
      toast.error(e.message || "Verification failed");
    }
  }

  return (
    <main className="relative min-h-dvh flex flex-col items-center justify-center bg-neutral-950 text-neutral-100 px-4 sm:px-6 text-center overflow-hidden">
      <video
        src="/video.mp4"
        autoPlay
        loop
        muted
        playsInline
        poster="/gif.gif"
        className="absolute inset-0 w-full h-full object-cover opacity-10 pointer-events-none"
      />
      <Image
        src="/cocoon/static/cocoon-logo-blue.png"
        alt="Cocoon logo"
        width={96}
        height={96}
        className="mb-4 opacity-80"
        priority
      />
      <h1 className="font-heading text-4xl sm:text-5xl md:text-6xl mb-6">Lay Science</h1>

      {step === "choice" && (
        <>
          <div className="space-y-4 w-full max-w-xs sm:max-w-sm md:max-w-md">
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
          <p className="mt-8 max-w-xl mx-auto text-neutral-200">
            LayScience makes research papers easy. Paste a DOI, link, or upload a PDF—get clear, engaging summaries in minutes. Instantly see the Problem → Solution → Impact in your language and style. Save time, spark curiosity, and unlock science for everyone.
          </p>
        </>
      )}
      {step === "register" && (
        <div className="space-y-4 w-full max-w-xs sm:max-w-sm md:max-w-md">
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
        <div className="space-y-4 w-full max-w-xs sm:max-w-sm md:max-w-md">
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
