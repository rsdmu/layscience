'use client'
import Button from './ui/Button'
export default function TTSButton({ text }:{ text:string }){
  return <Button variant="secondary" onClick={()=>{
    try { const u = new SpeechSynthesisUtterance(text); u.rate = 1; window.speechSynthesis.speak(u) } catch {}
  }}>🔊 Listen</Button>
}