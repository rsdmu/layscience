import type { Metadata } from "next";
import Welcome from "@/components/Welcome";

console.info("API base", process.env.NEXT_PUBLIC_API_BASE);

export const metadata: Metadata = {
  title: "Welcome",
  description:
    "Create an account or test Lay Science—the AI that turns research into clear, engaging summaries.",
};

export default function Page() {
  return <Welcome />;
}

