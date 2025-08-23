"use client";

import { useEffect, useState } from "react";
import UserPanel from "./UserPanel";

export default function UserFab() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<{ username?: string; email?: string } | null>(null);

  useEffect(() => {
    const username = localStorage.getItem("username") || undefined;
    const email = localStorage.getItem("email") || undefined;
    const hasAccount = localStorage.getItem("hasAccount") === "true";
    if (hasAccount && (username || email)) {
      setUser({ username, email });
    }
  }, []);

  if (!user) return null;

  function getInitials(user: { username?: string; email?: string }) {
    const name = user.username || "";
    if (name.trim().length === 0 && user.email) {
      return user.email.charAt(0).toUpperCase();
    }
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0][0].toUpperCase();
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed left-4 bottom-4 z-50 h-10 w-10 rounded-full flex items-center justify-center bg-neutral-800 text-white shadow-lg"
      >
        {getInitials(user)}
      </button>
      {open && <UserPanel onClose={() => setOpen(false)} user={user} />}
    </>
  );
}

