"use client";

import { useState } from "react";

interface Result {
  id: string;
  title: string;
}

export default function ArxivSearch({
  onSelect,
}: {
  onSelect: (url: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      setLoading(true);
      // Query arXiv's API for papers matching the search query
      const res = await fetch(
        `https://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(
          query.trim()
        )}&max_results=5`
      );
      const text = await res.text();
      const doc = new DOMParser().parseFromString(text, "application/xml");
      const entries = Array.from(doc.getElementsByTagName("entry"));
      const mapped = entries.map((entry) => ({
        id:
          entry.getElementsByTagName("id")[0]?.textContent || "",
        title:
          entry.getElementsByTagName("title")[0]?.textContent?.replace(/\s+/g, " ").trim() ||
          "",
      }));
      setResults(mapped);
    } catch (err) {
      // Swallow errors and show empty results
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      <form onSubmit={search} className="flex gap-2 mb-4">
        <input
          className="flex-1 bg-neutral-900/60 border border-neutral-700 rounded-full px-3 py-2 text-sm text-neutral-200"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search arXiv"
        />
        <button
          type="submit"
          className="border border-neutral-700 rounded-full px-4 py-2 text-sm text-neutral-400 hover:text-white bg-neutral-800"
        >
          {loading ? "..." : "Search"}
        </button>
      </form>
      <ul className="space-y-2">
        {results.map((r) => (
          <li key={r.id}>
            <button
              className="text-left w-full text-neutral-200 hover:underline"
              onClick={() => onSelect(r.id)}
            >
              {r.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

