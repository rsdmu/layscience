'use client'
import { useCallback, useState } from 'react'
import { getUploadUrl } from '@/lib/api'
import toast from 'react-hot-toast'

export default function Dropzone({ onUploaded }:{ onUploaded: (key:string)=>void }) {
  const [hover, setHover] = useState(false)
  const [busy, setBusy] = useState(false)

  const onDrop = useCallback(async (file: File) => {
    if (file.type !== 'application/pdf') { toast.error('Please drop a PDF'); return }
    setBusy(true)
    try {
      const { key, url } = await getUploadUrl()
      await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/pdf' }, body: file })
      toast.success('Uploaded')
      onUploaded(key)
    } catch (e:any) {
      toast.error(e.message || 'Upload failed')
    } finally { setBusy(false) }
  }, [onUploaded])

  return (
    <div
      onDragOver={e=>{e.preventDefault(); setHover(true)}}
      onDragLeave={()=>setHover(false)}
      onDrop={e=>{e.preventDefault(); setHover(false); const f = e.dataTransfer.files?.[0]; if (f) onDrop(f)}}
      className={`card border-dashed ${hover? 'border-accent shadow-glow': ''}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-semibold">Upload PDF (drag & drop)</div>
          <div className="small">Max 25MB. Your file is uploaded securely via a one-time URL.</div>
        </div>
        <label className="btn secondary cursor-pointer">
          <input type="file" accept="application/pdf" className="hidden" onChange={(e)=>{
            const f = e.target.files?.[0]; if (f) onDrop(f)
          }} />
          Choose file
        </label>
      </div>
      {busy && <div className="mt-3 text-sm opacity-80">Uploading…</div>}
    </div>
  )
}
