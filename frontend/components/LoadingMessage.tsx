"use client";

export default function LoadingMessage({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center gap-2 text-center text-neutral-500">
      <svg
        className="h-4 w-4 animate-spin text-neutral-400"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span>{message}</span>
    </div>
  );
}

