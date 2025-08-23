"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { searchArxiv } from "@/lib/api";

interface Props {
  onSelect: (pdfUrl: string) => void;
}

export default function ArxivSearch({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  async function doSearch() {
    if (!query.trim()) return;
    try {
      setBusy(true);
      const res = await searchArxiv(query.trim());
      setResults(res.results || []);
    } catch (e: any) {
      toast.error(e.message || "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto mt-8">
      <h2 className="text-center mb-4 text-neutral-200">Search arXiv</h2>
      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 bg-neutral-900/60 border border-neutral-700 rounded-full px-4 py-2 text-neutral-200"
          placeholder="Keywords or title"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") doSearch();
          }}
        />
        <button
          type="button"
          className="border border-neutral-700 bg-neutral-800 rounded-full px-4 py-2 text-neutral-200 disabled:opacity-50"
          onClick={doSearch}
          disabled={busy}
        >
          Search
        </button>
      </div>
      {results.length > 0 && (
        <ul className="space-y-4">
          {results.map((r) => (
            <li
              key={r.id}
              className="border border-neutral-700 rounded-lg p-4 bg-neutral-900/60"
            >
              <h3 className="text-neutral-100 font-semibold">{r.title}</h3>
              {r.authors && (
                <p className="text-neutral-400 text-sm">
                  {(r.authors as string[]).join(", ")}
                </p>
              )}
              {r.categories && (
                <p className="text-neutral-500 text-xs mb-2">
                  {(r.categories as string[]).join(", ")}
                </p>
              )}
              <div className="flex gap-2">
                <a
                  href={r.links?.html || `https://arxiv.org/abs/${r.id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 text-sm underline"
                >
                  View
                </a>
                {r.links?.pdf && (
                  <button
                    type="button"
                    className="text-neutral-200 text-sm border border-neutral-700 rounded px-2 py-1 hover:bg-neutral-800"
                    onClick={() => onSelect(r.links.pdf)}
                  >
                    Summarize
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
