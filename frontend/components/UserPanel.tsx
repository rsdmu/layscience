"use client";

import { useState } from "react";
import FeedbackTab from "./Feedback/FeedbackTab";

interface Props {
  onClose: () => void;
  user: { username?: string; email?: string };
}

function AccountTab({ user, onDelete }: { user: { username?: string; email?: string }; onDelete: () => void }) {
  return (
    <div className="space-y-4 text-sm">
      <p><strong>User:</strong> {user.username || user.email}</p>
      <p><strong>Email:</strong> {user.email}</p>
      <button
        type="button"
        onClick={onDelete}
        className="rounded bg-red-600/20 px-3 py-2 text-red-200 hover:bg-red-600/30"
      >
        Delete my account
      </button>
    </div>
  );
}

export default function UserPanel({ onClose, user }: Props) {
  const tabs = ["Feedback", "Account"] as const;
  type Tab = (typeof tabs)[number];
  const [tab, setTab] = useState<Tab>("Feedback");

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-start bg-black/30 px-4 pt-14 pb-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xs rounded-lg border border-neutral-700 bg-neutral-900 text-neutral-100 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex border-b border-neutral-700">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 text-sm font-medium hover:bg-neutral-800 ${
                tab === t ? "bg-neutral-800" : ""
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="p-4 max-h-80 overflow-y-auto">
          {tab === "Feedback" && <FeedbackTab />}
          {tab === "Account" && <AccountTab user={user} onDelete={() => {}} />}
        </div>
      </div>
    </div>
  );
}

