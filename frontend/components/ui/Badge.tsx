export default function Badge({ children }:{ children: React.ReactNode }) {
  return <span className="inline-flex items-center rounded-md border border-border bg-surface px-2 py-1 text-xs">{children}</span>
}