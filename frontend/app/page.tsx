'use client'

import { useMemo, useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import Hero from '@/components/Hero'
import Button from '@/components/ui/Button'
import Dropzone from '@/components/Dropzone'
import SummaryCard from '@/components/SummaryCard'
import Progress from '@/components/ui/Progress'
import { startJob, getStatus, getSummary } from '@/lib/api'

export default function Page() {
  const [doi, setDoi] = useState('')
  const [url, setUrl] = useState('')
  const [fileId, setFileId] = useState<string | null>(null)
  const [mode, setMode] = useState<'micro'|'extended'>('micro')
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [progress, setProgress] = useState<number>(0)
  const [summary, setSummary] = useState<any | null>(null)

  // Poll job status once started
  useEffect(() => {
    if (!jobId) return
    let t: any
    const tick = async () => {
      try {
        const s = await getStatus(jobId)
        setStatus(s.status)
        setProgress(p => Math.min(95, p + 10))
        if (s.status === 'done') {
          const res = await getSummary(jobId)
          setSummary(res.summary ? res.summary : res)
          setProgress(100)
          return
        }
        if (s.status === 'failed') {
          toast.error('The job failed. Check server logs.')
          return
        }
      } catch (e:any) {
        toast.error(e.message)
        return
      }
      t = setTimeout(tick, 1500)
    }
    tick()
    return () => clearTimeout(t)
  }, [jobId])

  async function onSummarise() {
    setSummary(null)
    setProgress(5)
    try {
      const r = await startJob({
        input: { doi: doi || undefined, url: url || undefined, file_id: fileId || undefined },
        mode,
        privacy: 'private'
      })
      setJobId(r.id)
      setStatus(r.status)
    } catch (e:any) {
      toast.error(e.message)
      setProgress(0)
    }
  }

  return (
    <main className="min-h-screen">
      <Hero />
      <section className="container-lg py-10 grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Controls */}
        <div className="space-y-4">
          <div className="card space-y-2">
            <div className="label">DOI</div>
            <input value={doi} onChange={e=>setDoi(e.target.value)} className="input" placeholder="10.1038/s41586-020-2649-2" />
            <div className="label mt-4">Or URL</div>
            <input value={url} onChange={e=>setUrl(e.target.value)} className="input" placeholder="https://example.com/paper.pdf" />
            <div className="my-4">
              <Dropzone onUploaded={(id)=>{ setFileId(id); toast.success('PDF uploaded') }} />
            </div>
            <div className="flex items-center gap-2">
              <label className="label mr-3">Mode</label>
              <select value={mode} onChange={e=>setMode(e.target.value as any)}
                      className="input max-w-[200px]">
                <option value="micro">Micro (3 sentences)</option>
                <option value="extended">Extended</option>
              </select>
              <Button className="ml-auto" onClick={onSummarise}>Summarise</Button>
            </div>
            {jobId && <Progress value={progress} />}
            {status && <p className="text-xs text-gray-500">Status: {status}</p>}
          </div>
        </div>

        {/* Summary column */}
        <div>
          {summary ? (
            <SummaryCard data={summary} />
          ) : (
            <div className="card text-center text-gray-500">
              <p>Submit a paper to see its summary here.</p>
            </div>
          )}
        </div>
      </section>
    </main>
  )
}
