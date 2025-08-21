'use client'
export default function PrivacySelect({ value, onChange }:{ value:'process-only'|'private'|'public', onChange:(v:'process-only'|'private'|'public')=>void }) {
  return (
    <div className="card">
      <div className="font-semibold mb-1">Privacy</div>
      <select className="select" value={value} onChange={(e)=>onChange(e.target.value as any)}>
        <option value="process-only">Process only (no storage)</option>
        <option value="private">Private library</option>
        <option value="public">Public link</option>
      </select>
      <div className="small mt-2 opacity-70">Process-only auto-deletes after ~1 hour.</div>
    </div>
  )
}
