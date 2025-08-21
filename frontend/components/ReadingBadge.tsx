import Badge from './ui/Badge'
export default function ReadingBadge({ grade, ease }:{ grade:number, ease:number }) {
  const txt = grade < 0 ? 'N/A' : `FK ${grade.toFixed(1)} • Ease ${ease.toFixed(0)}`
  const color = grade <= 12 || grade<0 ? '#00BFFF' : '#ff6b6b'
  return <Badge><span style={{color}}>{txt}</span></Badge>
}