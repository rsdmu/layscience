'use client'
import Button from './ui/Button'
import { translateSummary } from '@/lib/api'
import toast from 'react-hot-toast'
import { useState } from 'react'

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'pt', label: 'Português' },
  { code: 'zh', label: '中文' }
]

export default function TranslateBar({ id, onTranslated }:{ id: string, onTranslated: (obj:any)=>void }){
  const [target, setTarget] = useState('es')
  const [busy, setBusy] = useState(false)
  return (
    <div className="card">
      <div className="flex items-center gap-3">
        <select className="select w-auto" value={target} onChange={(e)=>setTarget(e.target.value)}>
          {LANGS.map(l=> <option key={l.code} value={l.code}>{l.label}</option>)}
        </select>
        <Button variant="secondary" disabled={busy} onClick={async()=>{
          setBusy(true)
          try {
            const res = await translateSummary(id, target)
            toast.success('Translated')
            onTranslated(res)
          } catch (e:any) { toast.error(e.message || 'Translate failed') }
          finally { setBusy(false) }
        }}>Translate</Button>
        <div className="small opacity-70">Show original English toggle is above the summary.</div>
      </div>
    </div>
  )
}
