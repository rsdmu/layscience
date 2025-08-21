'use client'
import Button from './ui/Button'

export default function ModeToggle({ mode, setMode }:{ mode:'micro'|'extended', setMode:(m:'micro'|'extended')=>void }){
  return (
    <div className="card">
      <div className="font-semibold mb-2">Summary length</div>
      <div className="flex gap-2">
        <Button variant={mode==='micro'?'primary':'secondary'} onClick={()=>setMode('micro')}>3‑sentence</Button>
        <Button variant={mode==='extended'?'primary':'secondary'} onClick={()=>setMode('extended')}>5‑paragraph</Button>
      </div>
      <div className="small mt-2 opacity-70">Test Version - AI can be baised.</div>
    </div>
  )
}
