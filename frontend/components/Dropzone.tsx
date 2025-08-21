'use client'

import { useRef, useState } from 'react'
import Button from './ui/Button'

type Props = { onUploaded: (fileId: string) => void }

export default function Dropzone({onUploaded}: Props) {
  const fileRef = useRef<HTMLInputElement|null>(null)
  const [busy, setBusy] = useState(false)

  async function upload(file: File) {
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const r = await fetch(process.env.NEXT_PUBLIC_API_BASE ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/upload` : '/api/proxy/api/v1/upload', {
        method: 'POST',
        body: form,
        cache: 'no-store',
      })
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()
      onUploaded(data.file_id)
    } catch (e:any) {
      alert(`Upload failed: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-2 border-dashed rounded-lg p-6 text-center bg-white">
      <input ref={fileRef} type="file" accept="application/pdf" hidden onChange={(e)=>{
        const file=e.target.files?.[0]; if(file) upload(file)
      }} />
      <p className="mb-2 text-sm text-gray-600">Drop a PDF here or choose a file</p>
      <Button onClick={()=>fileRef.current?.click()} disabled={busy}>{busy? 'Uploading…':'Choose PDF'}</Button>
    </div>
  )
}
