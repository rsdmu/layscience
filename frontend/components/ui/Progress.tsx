export default function Progress({ value }:{ value:number }) {
  return <div className="w-full h-2 bg-surface border border-border rounded-full overflow-hidden">
    <div className="h-full bg-accent" style={{width: `${Math.max(0, Math.min(100, value))}%`}} />
  </div>
}