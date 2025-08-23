import type { Metadata } from "next";
import Summarize from "@/components/Summarize";

export const metadata: Metadata = {
  title: "Summarize Research",
  description:
    "Upload a paper or enter a DOI/URL to get a concise AI-generated summary from Lay Science.",
};

export default function Page() {
  return <Summarize />;
}

