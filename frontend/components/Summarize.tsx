"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { startJob, getJob, getSummary, searchArxiv } from "@/lib/api";
// ArXiv search is now integrated directly into this component
import UserFab from "@/components/UserFab";

type HistoryItem = {
  type: "link" | "pdf";
  value: string;
  name?: string;
  title?: string;
};

type SummaryItem = {
  id: string;
  title?: string;
  content: string;
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
  const [summaries, setSummaries] = useState<SummaryItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [mode, setMode] = useState<"default" | "detailed" | "funny">("default");

  const [language, setLanguage] = useState<"en" | "fa" | "fr" | "es" | "de">("en");
  const [showArxiv, setShowArxiv] = useState(false);
  const [arxivResults, setArxivResults] = useState<any[]>([]);
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
    setArxivResults([]);
    setRef(url);
    setFile(null);
    onStart(url);
  }

  async function onSearchArxiv() {
    if (!ref.trim()) return;
    try {
      setBusy(true);
      const data = await searchArxiv(ref.trim());
      setArxivResults(data.results || []);
    } catch (e) {
      setArxivResults([]);
      toast.error("Search failed");
    } finally {
      setBusy(false);
    }
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
        if (s?.payload?.summary) {
          setSummary(s.payload.summary);
          setSummaries((prev) => {
            const newSummaries = [
              { id, title: s.payload.meta?.title, content: s.payload.summary },
              ...prev,
            ].slice(0, 20);
            localStorage.setItem("summaries", JSON.stringify(newSummaries));
            return newSummaries;
          });
        }

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
    const sum = localStorage.getItem("summaries");
    if (sum) {
      try {
        setSummaries(JSON.parse(sum));
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
        <div className="flex-1 flex flex-col">
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
          <div className="flex-1 overflow-y-auto mt-4 border-t border-neutral-800 pt-4">
            <p className="mb-2">Recent summaries:</p>
            {summaries.length > 0 ? (
              <ul className="space-y-1">
                {summaries.map((s, i) => (
                  <li key={i}>
                    <button
                      className="text-left text-neutral-400 hover:underline block truncate w-full"
                      onClick={() => {
                        setSummary(s.content);
                        setJobId(s.id);
                        setStatus("done");
                      }}
                    >
                      {s.title || `Summary ${i + 1}`}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-neutral-500">No recent summaries.</p>
            )}
          </div>
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
                  placeholder={showArxiv ? "Search arXiv" : "Upload a paper or enter a DOI/URL"}
                  value={ref}
                  onChange={(e) => setRef(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      showArxiv ? onSearchArxiv() : onStart();
                    }
                  }}
                />
              </div>
              <button
                type="button"
                className="text-neutral-400 hover:text-white disabled:opacity-50 w-full sm:w-auto flex items-center justify-center border border-neutral-700 bg-neutral-800 rounded-full px-4 py-2 sm:h-full"
                onClick={() => (showArxiv ? onSearchArxiv() : onStart())}
                disabled={busy}
              >
                {showArxiv ? "Search" : "Summarize"}
              </button>
              <button
                type="button"
                className="w-full sm:w-auto flex items-center justify-center border border-neutral-700 rounded-full px-4 py-2 sm:h-full text-neutral-400 hover:text-white bg-neutral-800"
                onClick={() => {
                  setShowArxiv((prev) => !prev);
                  setRef("");
                  setFile(null);
                  setArxivResults([]);
                }}
              >
                arXiv
              </button>
            </div>

            {!showArxiv && (
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
            )}

            {!showArxiv && file && (
              <p className="mt-2 text-xs text-neutral-400">
                Selected: {file.name}
              </p>
            )}
          </div>
        </section>

          <section className="mx-auto w-full max-w-4xl px-6 pb-16">
            {showArxiv ? (
              <div className="mt-4">
                {busy && <p className="text-center text-neutral-500">Searching...</p>}
                {arxivResults.length > 0 ? (
                  <div>
                    <div className="flex items-center justify-between text-sm text-neutral-400 px-1 mb-2">
                      <span>Search Results</span>
                      <span>Summrize</span>
                    </div>
                    <ul className="max-h-96 overflow-y-auto space-y-2">
                      {arxivResults.map((r) => (
                        <li
                          key={r.id}
                          className="flex items-start justify-between gap-2"
                        >
                          <a
                            href={r.links?.html || `https://arxiv.org/abs/${r.id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="flex-1 text-neutral-200 hover:underline break-words"
                          >
                            {r.title.replace(/\$/g, "")}
                          </a>
                          <button
                            onClick={() =>
                              handleArxivSelect(
                                r.links?.pdf ||
                                  r.links?.html ||
                                  `https://arxiv.org/abs/${r.id}`
                              )
                            }
                            className="text-neutral-400 hover:text-white"
                            aria-label="Summarize paper"
                          >
                            <svg
                              viewBox="0 0 24 24"
                              fill="none"
                              className="h-4 w-4"
                            >
                              <rect
                                x="3"
                                y="4"
                                width="18"
                                height="16"
                                rx="2"
                                stroke="currentColor"
                                strokeWidth="1.5"
                              />
                              <path
                                stroke="currentColor"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                d="M8 8h8M8 12h8M8 16h5"
                              />
                            </svg>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : ref && !busy ? (
                  <p className="text-center text-neutral-500">No results</p>
                ) : null}
              </div>
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
