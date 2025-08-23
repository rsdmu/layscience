"use client";

import { useState } from "react";
import Image from "next/image";
import toast from "react-hot-toast";
import { registerAccount, verifyCode } from "@/lib/api";

export default function RegisterPage() {
  const [step, setStep] = useState<"register" | "verify">("register");
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
    } catch (e: any) {
      toast.error(e.message || "Verification failed");
    }
  }

  return (
    <main className="min-h-dvh flex items-center justify-center bg-neutral-950 text-neutral-100 px-4">
      <div className="w-full max-w-md bg-neutral-900 rounded-lg p-8 space-y-6 shadow-lg">
        <div className="text-center">
          <Image
            src="/icon.png"
            alt="Lay Science logo"
            width={64}
            height={64}
            className="mx-auto mb-4 opacity-80"
          />
          <h1 className="font-heading text-3xl">Create account</h1>
        </div>

        {step === "register" && (
          <div className="space-y-4">
            <input
              className="w-full rounded bg-neutral-800 border border-neutral-700 px-3 py-2"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <input
              className="w-full rounded bg-neutral-800 border border-neutral-700 px-3 py-2"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <button
              className="w-full rounded bg-blue-500 hover:bg-blue-400 text-white py-2"
              onClick={onRegister}
            >
              Send verification code
            </button>
          </div>
        )}

        {step === "verify" && (
          <div className="space-y-4">
            <input
              className="w-full rounded bg-neutral-800 border border-neutral-700 px-3 py-2"
              placeholder="Verification code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <button
              className="w-full rounded bg-green-500 hover:bg-green-400 text-white py-2"
              onClick={onVerify}
            >
              Verify
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

