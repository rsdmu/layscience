'use client'
import { useEffect, useState } from 'react'
import { getSummary } from '@/lib/api'
import SummaryCard from '@/components/SummaryCard'

export default function SharePage({ params }:{ params: { id:string } }) {
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState<string|undefined>()
  useEffect(()=>{ getSummary(params.id).then(setData).catch(e=>setErr(e.message)) }, [params.id])
  if (err) return <div className="card">Error: {err}</div>
  if (!data) return <div className="card">Loading…</div>
  return <SummaryCard data={data} id={params.id}/>
}
