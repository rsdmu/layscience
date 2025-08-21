import React from 'react'

export default function Progress({value}:{value:number}) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-1.5 my-2">
      <div className="bg-black h-1.5 rounded-full transition-all" style={{width: `${value}%`}}/>
    </div>
  )
}
