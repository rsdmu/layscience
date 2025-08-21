import React from 'react'

type Summary = {
  title: string
  tldr: string
  key_points: string[]
  limitations: string[]
}

export default function SummaryCard({ data }:{data: Summary}) {
  return (
    <div className="card space-y-4">
      <h3 className="text-2xl font-display">{data.title}</h3>
      <p className="text-gray-800">{data.tldr}</p>
      <div>
        <div className="label mb-1">Key points</div>
        <ul className="list-disc ml-5 space-y-1">
          {data.key_points?.map((k, i)=> <li key={i}>{k}</li>)}
        </ul>
      </div>
      <div>
        <div className="label mb-1">Limitations</div>
        <ul className="list-disc ml-5 space-y-1">
          {data.limitations?.map((k, i)=> <li key={i}>{k}</li>)}
        </ul>
      </div>
    </div>
  )
}
