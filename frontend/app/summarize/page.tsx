"use client";

import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { startJob, getJob, getSummary } from "@/lib/api";

export default function Home() {
  const [ref, setRef] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "queued" | "running" | "done" | "failed">("idle");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [testCount, setTestCount] = useState(0);
  const [hasAccount, setHasAccount] = useState(false);

  function reset() {
    setJobId(null);
    setStatus("idle");
    setSummary("");
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }

  async function onStart() {
    if (!hasAccount && testCount >= 5) {
      toast.error("Test limit reached. Please create an account.");
      return;
    }
    try {
      setBusy(true);
      reset();
      const res = await startJob({ ref: ref || undefined, file, length: "default" });
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

  useEffect(() => {
    const hc = localStorage.getItem("hasAccount") === "true";
    setHasAccount(hc);
    const tc = parseInt(localStorage.getItem("testCount") || "0", 10);
    setTestCount(tc);
  }, []);

  useEffect(() => {
    if (summary && !hasAccount) {
      const newCount = testCount + 1;
      setTestCount(newCount);
      localStorage.setItem("testCount", newCount.toString());
    }
  }, [summary]);

  return (
    <main className="min-h-dvh flex flex-col bg-neutral-950 text-neutral-100">
        <section className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <h1 className="font-heading text-4xl sm:text-5xl mb-2">Lay Science</h1>
          <p className="text-neutral-400 mb-8 text-sm sm:text-base">AI that turns research into clear, engaging summaries.</p>
          {!hasAccount && (
            <p className="text-neutral-400 mb-4 text-sm">Tests remaining: {Math.max(0,5 - testCount)}</p>
          )}
          <div className="w-full max-w-xl">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 rounded-2xl sm:rounded-full border border-neutral-700 bg-neutral-900/60 px-4 py-3 focus-within:ring-2 focus-within:ring-white/30">
              <div className="flex items-center gap-2 flex-1">
                <label className="cursor-pointer text-neutral-400 hover:text-white">
                  <input
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                  <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
                    <path stroke="currentColor" strokeWidth="1.5" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                </label>
                <input
                  className="flex-1 bg-transparent text-neutral-200 placeholder:text-neutral-500 outline-none"
                  placeholder="Upload a paper or enter a DOI/URL"
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') onStart(); }}
                />
              </div>
              <button
                type="button"
                className="text-neutral-400 hover:text-white disabled:opacity-50 w-full sm:w-auto flex items-center justify-center border border-neutral-700 bg-neutral-800 rounded-full px-4 py-2 sm:h-full"
                onClick={onStart}
                disabled={busy}
              >
                Summarize
              </button>
            </div>
            {file && <p className="mt-2 text-xs text-neutral-400">Selected: {file.name}</p>}
          </div>
        </section>

      <section className="mx-auto w-full max-w-4xl px-6 pb-16">
        {summary ? (
          <article className="rounded-2xl border border-white/10 bg-neutral-950/60 p-6 leading-relaxed">
            <h2 className="font-heading text-2xl mb-3 text-white">Summary</h2>
            <div
              className="text-neutral-200 whitespace-pre-wrap"
              dangerouslySetInnerHTML={{
                __html: summary
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br/>'),
              }}
            />
          </article>
        ) : status === "running" || status === "queued" ? (
          <p className="text-center text-neutral-500">Generating summary...</p>
        ) : null}
      </section>
    </main>
  );
}

