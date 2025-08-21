/*
 * Home page for the LayScience application.
 *
 * This redesign embraces a light, airy aesthetic inspired by modern
 * scientific websites.  A prominent header introduces the app and
 * guides users through entering a DOI/URL or uploading a PDF.  The
 * summarisation process is started with a single button.  While the
 * job is running a progress bar provides feedback.  Once the summary
 * is ready it appears on the right side of the layout in a card.
 */

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
  const [s3Key, setS3Key] = useState<string | undefined>(undefined)
  const [mode, setMode] = useState<'micro' | 'extended'>('micro')
  const [privacy, setPrivacy] = useState<'process-only' | 'private' | 'public'>('process-only')
  const [jobId, setJobId] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [progress, setProgress] = useState<number>(0)
  const [summary, setSummary] = useState<any | null>(null)

  // Upload callback from Dropzone
  const handleUploaded = (key: string) => {
    setS3Key(key)
    toast.success('PDF uploaded successfully')
  }

  // Kick off summarisation
  async function run() {
    const input: any = {}
    if (doi.trim()) input.doi = doi.trim()
    else if (url.trim()) input.url = url.trim()
    else if (s3Key) input.s3_key = s3Key
    else {
      toast.error('Provide a DOI, URL or upload a PDF before summarising')
      return
    }
    try {
      const { id } = await startJob({ input, mode, privacy })
      setJobId(id)
      setStatus('running')
      setProgress(5)
      setSummary(null)
      toast.success('Summary job started')
    } catch (e: any) {
      toast.error(e.message || 'Failed to start job')
    }
  }

  // Poll job status until completed
  useEffect(() => {
    if (!jobId) return
    const timer = setInterval(async () => {
      try {
        const s = await getStatus(jobId)
        setStatus(s.status)
        setProgress((p) => Math.min(95, p + 10))
        if (s.status === 'done') {
          const data = await getSummary(jobId)
          setSummary(data)
          setProgress(100)
          clearInterval(timer)
          // Update the URL without a reload for sharing
          if (typeof window !== 'undefined') {
            history.replaceState({}, '', `/s/${jobId}`)
          }
          toast.success('Summary ready')
        }
      } catch (e) {
        console.error(e)
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [jobId])

  return (
    <main className="container py-10">
      <section className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-3">LayScience</h1>
        <p className="text-lg text-gray-700 max-w-2xl mx-auto">
          Turn research papers into concise, evidence‑grounded lay summaries. Paste a DOI, enter a URL or upload a PDF to get started.
        </p>
      </section>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Input and controls column */}
        <div className="space-y-6">
          <div className="card space-y-4">
            <div className="space-y-2">
              <label className="block text-sm font-semibold" htmlFor="doi">DOI</label>
              <input
                id="doi"
                className="input"
                type="text"
                placeholder="10.1000/xyz123"
                value={doi}
                onChange={(e) => setDoi(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-semibold" htmlFor="url">URL</label>
              <input
                id="url"
                className="input"
                type="url"
                placeholder="https://example.com/paper.pdf"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-semibold">Upload PDF</label>
              <Dropzone onUploaded={handleUploaded} />
              <p className="small">Max 25MB. Your file is uploaded securely via a one‑time URL.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-4 items-center">
            <ModeToggle mode={mode} setMode={setMode} />
            <PrivacySelect value={privacy} onChange={setPrivacy} />
          </div>
          <div>
            <Button onClick={run} className="w-full md:w-auto">Summarise</Button>
          </div>
          {status && (
            <div className="card">
              <p className="font-semibold mb-2">Status: {status}</p>
              {status !== 'done' && <Progress value={progress} />}
            </div>
          )}
        </div>
        {/* Summary column */}
        <div>
          {summary ? (
            <SummaryCard data={summary} id={jobId} />
          ) : (
            <div className="card text-center text-gray-500">
              <p>Submit a paper to see its summary here.</p>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}