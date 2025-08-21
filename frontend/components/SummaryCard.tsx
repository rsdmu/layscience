'use client'
import ReadingBadge from './ReadingBadge'
import TTSButton from './TTSButton'
import Button from './ui/Button'
import toast from 'react-hot-toast'
import { useState } from 'react'

export default function SummaryCard({ data, id }:{ data:any, id?:string }) {
  const [showOriginal, setShowOriginal] = useState(true)
  const jsonText = JSON.stringify(data, null, 2)
  const hasTranslation = !!data.lay_summary_translated
  const summary = hasTranslation && !showOriginal ? data.lay_summary_translated : data.lay_summary
  const paragraphs = (summary || '').split(/\n{2,}/g)

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-4">
        <h2 className="text-2xl font-bold" style={{color:'#00BFFF'}}>{data.headline}</h2>
        <div className="flex gap-2">
          <TTSButton text={summary} />
          <Button variant="secondary" onClick={()=>{navigator.clipboard.writeText(jsonText); toast.success('JSON copied')}}>Copy JSON</Button>
          {id && <Button variant="secondary" onClick={async ()=>{
            const url = (typeof window !== 'undefined') ? `${window.location.origin}/s/${id}` : ''
            await navigator.clipboard.writeText(url)
            toast.success('Share link copied')
          }}>Share</Button>}
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3">
        <ReadingBadge grade={Number(data?.reading_level?.flesch_kincaid_grade ?? -1)} ease={Number(data?.reading_level?.flesch_reading_ease ?? -1)} />
        <div className="small">{data.disclaimers?.length ? data.disclaimers.join(' • ') : null}</div>
      </div>

      {hasTranslation && (
        <div className="mt-2 small">
          <label>
            <input type="checkbox" checked={showOriginal} onChange={()=>setShowOriginal(!showOriginal)} /> Show original English
          </label>
        </div>
      )}

      <div className="mt-4 space-y-4">
        {paragraphs.map((p:string, i:number)=>(<p key={i}>{p}</p>))}
      </div>

      {Array.isArray(data.sentences) && data.sentences.length > 0 && (
        <div className="mt-6">
          <div className="font-semibold mb-2">Evidence</div>
          <ol className="list-decimal ml-6 space-y-2 text-sm opacity-90">
            {data.sentences.map((s:any, i:number)=>(
              <li key={i}>
                {s.text}
                {Array.isArray(s.citations) && s.citations.length > 0 && (
                  <span className="ml-2 opacity-70">[{s.citations.join(', ')}]</span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}

      {data.jargon_definitions && Object.keys(data.jargon_definitions).length > 0 && (
        <div className="mt-6">
          <div className="font-semibold mb-2">Glossary</div>
          <ul className="grid sm:grid-cols-2 gap-2 text-sm opacity-90">
            {Object.entries(data.jargon_definitions).map(([term,def]:any)=> (
              <li key={term} className="border border-border rounded-md p-2">
                <span className="text-accent">{term}</span> — {def as string}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
