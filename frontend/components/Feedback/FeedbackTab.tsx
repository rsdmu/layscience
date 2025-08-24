"use client";

import { useState, FormEvent } from "react";
import { submitFeedbackSurvey } from "@/lib/api";

export default function FeedbackTab() {
  const [ease, setEase] = useState(3);
  const [clarity, setClarity] = useState(3);
  const [improvement, setImprovement] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await submitFeedbackSurvey(ease, clarity, improvement);
      setSubmitted(true);
      setImprovement("");
    } catch (err) {
      setError("Failed to send feedback");
    }
  }

  if (submitted) {
    return <p className="text-sm text-green-200">Thanks for your feedback!</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 text-sm">
      <label className="block">
        <span className="mb-1 block">How easy was it to find what you needed?</span>
        <select
          value={ease}
          onChange={(e) => setEase(Number(e.target.value))}
          className="w-full rounded bg-neutral-800 p-2"
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="mb-1 block">Is the interface visually clear?</span>
        <select
          value={clarity}
          onChange={(e) => setClarity(Number(e.target.value))}
          className="w-full rounded bg-neutral-800 p-2"
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="mb-1 block">What&apos;s one improvement you&apos;d like to see?</span>
        <textarea
          value={improvement}
          onChange={(e) => setImprovement(e.target.value)}
          maxLength={100}
          className="w-full rounded bg-neutral-800 p-2"
        />
      </label>

      {error && <p className="text-red-400">{error}</p>}

      <button
        type="submit"
        className="rounded bg-blue-600/20 px-3 py-2 text-blue-200 hover:bg-blue-600/30"
      >
        Submit
      </button>
    </form>
  );
}

