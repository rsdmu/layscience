"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function AboutHomeLink() {
  const pathname = usePathname();
  const isAbout = pathname?.startsWith("/about");
  const [hasAccount, setHasAccount] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setHasAccount(localStorage.getItem("hasAccount") === "true");
    }
  }, []);

  const href = isAbout ? (hasAccount ? "/summarize" : "/") : "/about";

  return (
    <Link
      href={href}
      prefetch={false}
      className="fixed top-2 right-2 z-50 text-xs text-neutral-400 hover:text-neutral-200"
    >
      {isAbout ? "home" : "about"}
    </Link>
  );
}
