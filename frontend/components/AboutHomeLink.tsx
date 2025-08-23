"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AboutHomeLink() {
  const pathname = usePathname();
  const isAbout = pathname?.startsWith("/about");

  return (
    <Link
      href={isAbout ? "/" : "/about"}
      className="fixed top-2 right-2 text-xs text-neutral-400 hover:text-neutral-200"
    >
      {isAbout ? "home" : "about"}
    </Link>
  );
}
