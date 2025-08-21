
"use client";

import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { startJob, getJob, getSummary } from "@/lib/api";

export default function Home() {
  const [ref, setRef] = useState(""); // DOI or URL
  const [file, setFile] = useState<File | null>(null);
  const [length, setLength] = useState<"default" | "extended">("default");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "queued" | "running" | "done" | "failed">("idle");
  const [summary, setSummary] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function reset() {
    setJobId(null);
    setStatus("idle");
    setSummary(""); 
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }

  async function onStart() {
    try {
      setBusy(true);
      setSummary(""); 
      const res = await startJob({ ref: ref || undefined, file, length });
      setJobId(res.id);
      setStatus("queued");
      toast.success("Job started");
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(() => poll(res.id), 1500);
    } catch (e: any) {
      toast.error(e.message || "Failed to start job");
    } finally {
      setBusy(false);
    }
  }

  async function poll(id: string) {
    try {
      const j = await getJob(id);
      setStatus(j.status);
      if (j.status === "failed") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        const err = j.error?.message || JSON.stringify(j.error);
        toast.error(`Failed: ${err}`);
      }
      if (j.status === "done") {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        const s = await getSummary(id);
        if (s?.payload?.summary) setSummary(s.payload.summary);
      }
    } catch (e) {
      // ignore transient errors
    }
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  return (
    <main className="min-h-dvh bg-neutral-950 text-neutral-100">
      <section className="mx-auto max-w-4xl px-6 py-10">
        <h1 className="text-3xl font-bold mb-4">LayScience</h1>
        <p className="text-neutral-400 mb-6">Enter a DOI or URL, or upload a PDF. Choose Default (≈200 words) or Extended (≈350 words).</p>

        <div className="rounded-2xl border border-white/10 bg-neutral-900/50 p-5 space-y-4">
          <div className="space-y-1">
            <label className="block text-sm text-neutral-300">DOI or URL</label>
            <input
              className="w-full rounded-md bg-neutral-800 px-3 py-2 outline-none ring-1 ring-neutral-700 focus:ring-white/30"
              placeholder="10.xxxx/..., https://..."
              value={ref}
              onChange={(e) => setRef(e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="block text-sm text-neutral-300">PDF (optional)</label>
            <input
              type="file" accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-neutral-200"
            />
            {file && <p className="text-xs text-neutral-400">Selected: {file.name}</p>}
          </div>

          <div className="flex items-center gap-4">
            <label className="text-sm">Length</label>
            <select
              className="rounded-md bg-neutral-800 px-3 py-2 outline-none ring-1 ring-neutral-700 focus:ring-white/30"
              value={length}
              onChange={(e) => setLength(e.target.value as any)}
            >
              <option value="default">Default (≈200 words)</option>
              <option value="extended">Extended (≈350 words)</option>
            </select>
          </div>

          <div className="flex gap-3">
            <button
              onClick={onStart}
              disabled={busy}
              className="rounded-md bg-white text-black px-4 py-2 font-medium hover:bg-neutral-200 disabled:opacity-60"
            >
              Summarize
            </button>
            <button onClick={reset} className="rounded-md border border-white/20 px-4 py-2">Reset</button>
            {jobId && <span className="text-sm text-neutral-400">Job: {jobId}</span>}
            {status !== "idle" && <span className="text-sm text-neutral-400">Status: {status}</span>}
          </div>
        </div>
      </section>

      {/* SUMMARY */}
      <section className="mx-auto max-w-4xl px-6 pb-20">
        {summary ? (
          <article className="rounded-2xl border border-white/10 bg-neutral-950/60 p-6 leading-relaxed">
            <h2 className="font-heading text-2xl mb-3 text-white">Summary</h2>
            <pre className="whitespace-pre-wrap text-neutral-200">{summary}</pre>
          </article>
        ) : (
          <p className="text-neutral-500">No summary yet.</p>
        )}
      </section>
    </main>
  );
}
