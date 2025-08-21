'use client'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import Button from '@/components/ui/Button'
import Dropzone from '@/components/Dropzone'
import ModeToggle from '@/components/ModeToggle'
import PrivacySelect from '@/components/PrivacySelect'
import SummaryCard from '@/components/SummaryCard'
import Progress from '@/components/ui/Progress'
import { startJob, getStatus, getSummary } from '@/lib/api'

export default function Home() {
  const [doi, setDoi] = useState('')
  const [url, setUrl] = useState('')
  const [s3Key, setS3Key] = useState<string|undefined>()
  const [mode, setMode] = useState<'micro'|'extended'>('micro')
  const [privacy, setPrivacy] = useState<'process-only'|'private'|'public'>('process-only')
  const [jobId, setJobId] = useState<string|undefined>()
  const [status, setStatus] = useState<string|undefined>()
  const [progress, setProgress] = useState(15)
  const [summary, setSummary] = useState<any>(null)

  async function run() {
    const input:any = {}
    if (doi.trim()) input.doi = doi.trim()
    else if (url.trim()) input.url = url.trim()
    else if (s3Key) input.s3_key = s3Key
    else { toast.error('Provide a DOI, URL, or upload a PDF'); return }

    try {
      const { id } = await startJob({ input, mode, privacy })
      setJobId(id); setStatus('running'); setProgress(20); setSummary(null)
      toast.success('Job started')
    } catch (e:any) {
      toast.error(e.message || 'Failed to start job')
    }
  }

  useEffect(()=>{
    if (!jobId) return
    const t = setInterval(async ()=>{
      try {
        const s = await getStatus(jobId)
        setStatus(s.status)
        setProgress(p=> Math.min(95, p + 8))
        if (s.status === 'done') {
          const data = await getSummary(jobId)
          setSummary(data)
          setProgress(100)
          clearInterval(t)
          history.replaceState({}, '', `/s/${jobId}`)
          toast.success('Summary ready')
        }
      } catch {}
    }, 1200)
    return ()=>clearInterval(t)
  }, [jobId])

  return (
    <div className="space-y-6">
      <section className="card relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" style={{background:'radial-gradient(600px 200px at 80% -20%, rgba(0,191,255,.15), transparent), radial-gradient(400px 160px at 20% 0%, rgba(0,191,255,.08), transparent)'}} />
        <div className="relative">
          <h1 className="text-4xl font-bold mb-2">Summarize research papers</h1>
          <p className="opacity-80 mb-4">Paste a DOI/URL or upload a PDF.</p>
          <div className="grid sm:grid-cols-2 gap-3">
            <input className="input" placeholder="DOI e.g., 10.xxxx/xxxxx" value={doi} onChange={e=>setDoi(e.target.value)} />
            <input className="input" placeholder="Paper URL e.g., https://..." value={url} onChange={e=>setUrl(e.target.value)} />
          </div>
          <div className="mt-3">
            <Dropzone onUploaded={setS3Key} />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={run}>Summarize</Button>
            {status && <span className="small">Status: {status}</span>}
          </div>
          {status && status !== 'done' && (
            <div className="mt-3"><Progress value={progress}/></div>
          )}
        </div>
      </section>

      <div className="grid md:grid-cols-2 gap-4">
        <ModeToggle mode={mode} setMode={setMode} />
        <PrivacySelect value={privacy} onChange={setPrivacy} />
      </div>

      

      {summary && (
        <section>
          <SummaryCard data={summary} id={jobId} />
        </section>
      )}
    </div>
  )
}
