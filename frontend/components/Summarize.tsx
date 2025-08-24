"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { startJob, getJob, getSummary } from "@/lib/api";
import ArxivSearch from "@/components/ArxivSearch";
import UserFab from "@/components/UserFab";

type HistoryItem = {
  type: "link" | "pdf";
  value: string;
  name?: string;
  title?: string;
};

export default function Summarize() {
  const [ref, setRef] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "queued" | "running" | "done" | "failed">("idle");
  const [summary, setSummary] = useState("");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [testCount, setTestCount] = useState(0);
  const [hasAccount, setHasAccount] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [mode, setMode] = useState<"default" | "detailed" | "funny">("default");

  const [language, setLanguage] = useState<"en" | "fa" | "fr" | "es" | "de">("en");
  const [showArxiv, setShowArxiv] = useState(false);
  const summaryRef = useRef<HTMLElement | null>(null);

  function reset() {
    setJobId(null);
    setStatus("idle");
    setSummary("");
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function addToHistory(item: HistoryItem) {
    setHistory((prev) => {
      const newHistory = [item, ...prev];
      const toPersist = newHistory
        .filter((h) => h.type === "link")
        .slice(0, 20);
      localStorage.setItem("history", JSON.stringify(toPersist));
      return newHistory;
    });
  }

  async function onStart(overrideRef?: string) {
    if (!hasAccount && testCount >= 5) {
      toast.error("Test limit reached. Please create an account.");
      return;
    }
    try {
      setBusy(true);
      reset();
      const usedRef = overrideRef || ref;

      if (overrideRef) {
        addToHistory({ type: "link", value: overrideRef });
      } else if (file) {
        const url = URL.createObjectURL(file);
        addToHistory({ type: "pdf", value: url, name: file.name });
      } else if (ref) {
        addToHistory({ type: "link", value: ref });
      }

      const res = await startJob({
        ref: usedRef || undefined,
        file: overrideRef ? undefined : file,
        length: mode === "detailed" ? "extended" : "default",
        mode,
        language,
      });
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

  function handleArxivSelect(url: string) {
    setShowArxiv(false);
    setRef(url);
    setFile(null);
    onStart(url);
  }

  async function poll(id: string) {
    try {
      const j = await getJob(id);
      setStatus(j.status);

      if (j.status === "failed") {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        const err = j.error?.message || JSON.stringify(j.error);
        toast.error(`Failed: ${err}`);
      }

      if (j.status === "done") {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        const s = await getSummary(id);
        if (s?.payload?.summary) setSummary(s.payload.summary);

        if (s?.payload?.meta?.title) {
          setHistory((prev) => {
            if (prev.length === 0) return prev;
            const [first, ...rest] = prev;
            const updated = { ...first, title: s.payload.meta.title };
            const newHistory = [updated, ...rest];
            const toPersist = newHistory
              .filter((h) => h.type === "link")
              .slice(0, 20);
            localStorage.setItem("history", JSON.stringify(toPersist));
            return newHistory;
          });
        }
      }
    } catch {
      // ignore transient errors
    }
  }

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    const hc = localStorage.getItem("hasAccount") === "true";
    setHasAccount(hc);
    const tc = parseInt(localStorage.getItem("testCount") || "0", 10);
    setTestCount(tc);
    const hist = localStorage.getItem("history");
    if (hist) {
      try {
        setHistory(JSON.parse(hist));
      } catch {}
    }
  }, []);

  // Increment test counter once per summary generation (avoid testCount in deps to prevent loop)
  useEffect(() => {
    if (summary && !hasAccount) {
      setTestCount((prev) => {
        const newCount = prev + 1;
        localStorage.setItem("testCount", newCount.toString());
        return newCount;
      });
    }
  }, [summary, hasAccount]);

  // Center the summary into view when it appears
  useEffect(() => {
    if (summary && summaryRef.current) {
      summaryRef.current.scrollIntoView({
        behavior: "smooth",
        block: "center",
        inline: "center",
      });
    }
  }, [summary]);

  return (
    <main className="min-h-dvh flex bg-neutral-950 text-neutral-100">
      <aside className="w-full max-w-xs max-h-dvh border-r border-neutral-800 p-4 text-sm text-neutral-400 flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <p className="mb-2">Recent references:</p>
          {history.length > 0 ? (
            <ul className="space-y-1">
              {history.map((h, i) => (
                <li key={i}>
                  {h.type === "pdf" ? (
                    <a
                      href={h.value}
                      target="_blank"
                      rel="noopener"
                      className="text-neutral-400 hover:underline block truncate"
                    >
                      {h.title || h.name || "PDF"}
                    </a>
                  ) : (
                    <a
                      href={
                        h.value.startsWith("http")
                          ? h.value
                          : `https://doi.org/${h.value}`
                      }
                      target="_blank"
                      rel="noopener"
                      className="text-neutral-400 hover:underline block truncate"
                      draggable
                      onDragStart={(e) => {
                        // Provide both plain text and URI formats for drop targets
                        e.dataTransfer.setData("text/plain", h.value);
                        const url = h.value.startsWith("http")
                          ? h.value
                          : `https://doi.org/${h.value}`;
                        e.dataTransfer.setData("text/uri-list", url);
                      }}
                    >
                      {h.title || h.value}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-neutral-500">No recent references.</p>
          )}
        </div>
        <p className="mt-4 text-xs text-neutral-500">
          AI can make mistakes. LayScience is still in test.
        </p>
      </aside>
      <div className="flex-1 flex flex-col relative">
        <div className="absolute top-4 left-4">
          <UserFab />
        </div>
        <section className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <h1 className="font-heading text-4xl sm:text-5xl mb-2">Lay Science</h1>
          <p className="text-neutral-400 mb-8 text-sm sm:text-base">
            AI that turns research into clear, engaging summaries.
          </p>
          {!hasAccount &&
            (testCount < 5 ? (
              <p className="text-neutral-400 mb-4 text-sm">
                Tests remaining: {5 - testCount}
              </p>
            ) : (
              <div className="text-neutral-400 mb-4 text-sm flex flex-col items-center gap-2">
                <p>Test limit reached.</p>
                <Link
                  href="/"
                  className="rounded bg-white/10 px-3 py-1 text-neutral-100 hover:bg-white/20"
                >
                  Create account
                </Link>
              </div>
            ))}

          <div className="w-full max-w-xl">
            <div
              className={`flex flex-col sm:flex-row items-stretch sm:items-center gap-2 rounded-2xl sm:rounded-full border border-neutral-700 bg-neutral-900/60 px-4 py-3 focus-within:ring-2 focus-within:ring-white/30 ${
                dragOver ? "ring-2 ring-white/30" : ""
              }`}
              onDragOver={(e) => {
                if (showArxiv) return;
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={(e) => {
                if (showArxiv) return;
                e.preventDefault();
                setDragOver(false);
              }}
              onDrop={(e) => {
                if (showArxiv) return;
                e.preventDefault();
                setDragOver(false);
                const dropped = e.dataTransfer.files?.[0];
                const link =
                  e.dataTransfer.getData("text/uri-list") ||
                  e.dataTransfer.getData("text/plain");
                if (dropped) {
                  setFile(dropped);
                  setRef("");
                } else if (link) {
                  setFile(null);
                  setRef(link);
                  onStart(link);
                }
              }}
            >
              <div className="flex items-center gap-2 flex-1">
                {!showArxiv && (
                  <label className="cursor-pointer text-neutral-400 hover:text-white">
                    <input
                      type="file"
                      accept="application/pdf"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
                      <path
                        stroke="currentColor"
                        strokeWidth="1.5"
                        d="M12 4.5v15m7.5-7.5h-15"
                      />
                    </svg>
                  </label>
                )}
                <input
                  className="flex-1 bg-transparent text-neutral-200 placeholder:text-neutral-500 outline-none"
                  placeholder="Upload a paper or enter a DOI/URL"
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onStart();
                  }}
                />
              </div>
              <button
                type="button"
                className="text-neutral-400 hover:text-white disabled:opacity-50 w-full sm:w-auto flex items-center justify-center border border-neutral-700 bg-neutral-800 rounded-full px-4 py-2 sm:h-full"
                onClick={() => onStart()}
                disabled={busy}
              >
                Summarize
              </button>
              <button
                type="button"
                className="w-full sm:w-auto flex items-center justify-center border border-neutral-700 rounded-full px-4 py-2 sm:h-full text-neutral-400 hover:text-white bg-neutral-800"
                onClick={() => {
                  setShowArxiv((prev) => !prev);
                  setRef("");
                  setFile(null);
                }}
              >
                arXiv
              </button>
            </div>

            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <select
                className="bg-neutral-900/60 border border-neutral-700 rounded-full px-3 py-2 text-sm text-neutral-200 w-auto"
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
              >
                <option value="default">Default</option>
                <option value="detailed">Detailed</option>
                <option value="funny">Funny</option>
              </select>
              <select
                className="bg-neutral-900/60 border border-neutral-700 rounded-full px-3 py-2 text-sm text-neutral-200 w-auto"
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
              >
                <option value="en">English</option>
                <option value="fa">Persian</option>
                <option value="fr">French</option>
                <option value="es">Spanish</option>
                <option value="de">German</option>
              </select>
            </div>

            {!showArxiv && file && (
              <p className="mt-2 text-xs text-neutral-400">
                Selected: {file.name}
              </p>
            )}
          </div>
        </section>

        <section className="mx-auto w-full max-w-4xl px-6 pb-16">
          {showArxiv ? (
            <ArxivSearch onSelect={handleArxivSelect} />
          ) : summary ? (
            <article
              ref={summaryRef}
              className="rounded-2xl border border-white/10 bg-neutral-950/60 p-6 leading-relaxed"
            >
              <div
                className="text-neutral-200 whitespace-pre-wrap"
                dangerouslySetInnerHTML={{
                  __html: summary
                    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                    .replace(/\n/g, "<br/>"),
                }}
              />
            </article>
          ) : status === "running" || status === "queued" ? (
            <p className="text-center text-neutral-500">Generating summary...</p>
          ) : null}
        </section>
      </div>
    </main>
  );
}
