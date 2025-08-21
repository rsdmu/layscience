"use client";

import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { startJob, uploadFile, getJob, getSummary } from "@/lib/api";

export default function Home() {
  const [doi, setDoi] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "failed">("idle");
  const [summary, setSummary] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, []);

  async function onSubmit() {
    if (!doi && !url && !file) {
      toast.error("Provide a DOI, a URL, or upload a PDF.");
      return;
    }
    setBusy(true); setSummary(""); setStatus("running"); setJobId(null);

    try {
      let file_id: string | undefined;
      if (file) {
        const up = await uploadFile(file);
        file_id = up.file_id;
      }
      const job = await startJob({ doi: doi || undefined, url: url || undefined, file_id });
      setJobId(job.id);

      pollRef.current = setInterval(async () => {
        try {
          const s = await getJob(job.id);
          setStatus(s.status);
          if (s.status === "done") {
            if (pollRef.current) clearInterval(pollRef.current);
            const r = await getSummary(job.id);
            setSummary(r.summary?.text || JSON.stringify(r, null, 2));
            setBusy(false);
          } else if (s.status === "failed") {
            if (pollRef.current) clearInterval(pollRef.current);
            setBusy(false);
            toast.error(s.error || "Job failed");
          }
        } catch (e: any) {
          if (pollRef.current) clearInterval(pollRef.current);
          setBusy(false);
          toast.error(e.message || "Polling error");
        }
      }, 1500);
    } catch (e: any) {
      setBusy(false); setStatus("idle");
      toast.error(e.message || "Could not start the job");
    }
  }

  return (
    <main className="min-h-screen">
      {/* HERO */}
      <section className="bg-hero-gradient bg-lines">
        <div className="mx-auto max-w-5xl px-6 py-12">
          <div className="border-b border-white/10 pb-8">
            <h1 className="font-heading text-6xl md:text-8xl tracking-tight text-white">LAYSCIENCE</h1>
            <p className="mt-3 text-neutral-400 max-w-2xl">
              Summarise scientific papers in plain language.
            </p>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
            <input
              value={doi} onChange={e=>setDoi(e.target.value)}
              placeholder="DOI (e.g., 10.1038/s41586-020-2649-2)"
              className="rounded-xl bg-neutral-900/70 border border-white/10 px-4 py-3 outline-none focus:ring-2 focus:ring-white/20"
            />
            <input
              value={url} onChange={e=>setUrl(e.target.value)}
              placeholder="Direct PDF URL"
              className="rounded-xl bg-neutral-900/70 border border-white/10 px-4 py-3 outline-none focus:ring-2 focus:ring-white/20"
            />
            <label className="relative overflow-hidden rounded-xl border border-dashed border-white/20 bg-neutral-900/50 hover:bg-neutral-900/70 transition cursor-pointer">
              <input type="file" accept="application/pdf" className="absolute inset-0 opacity-0 cursor-pointer"
                onChange={e=>setFile(e.target.files?.[0] || null)} />
              <div className="h-full w-full px-4 py-3 text-neutral-400">
                {file ? `📄 ${file.name}` : "Drop PDF or click to upload"}
              </div>
            </label>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button onClick={onSubmit} disabled={busy}
              className="rounded-xl bg-white text-black px-5 py-3 font-semibold hover:bg-white/90 disabled:opacity-50">
              {busy ? "Summarising…" : "Summarise"}
            </button>
            {status === "running" && (
              <span className="text-neutral-400">
                Job running…{jobId ? ` (${jobId.slice(0,8)}…)` : ""}
              </span>
            )}
          </div>
        </div>
      </section>

      {/* SUMMARY */}
      <section className="mx-auto max-w-4xl px-6 py-10">
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
