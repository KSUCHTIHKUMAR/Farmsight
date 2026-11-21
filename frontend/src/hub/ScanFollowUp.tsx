import { useState } from 'react'
import { cropForLabel, getCrop, matchScanLabel } from './crops'
import { addJournalEntry } from './store'
import { todayISO } from './planner'
import { display } from './ui'

// Additive follow-up actions shown under a scan result. Does not read or alter the model output.
export default function ScanFollowUp({
  task,
  label,
  confidence,
  isHealthy,
  onLearn,
}: {
  task: 'leaf' | 'produce' | 'pest'
  label: string
  confidence: number
  isHealthy: boolean
  onLearn?: (cropId: string, diseaseId: string, label: string) => void
}) {
  const [saved, setSaved] = useState(false)
  const link = task === 'leaf' && !isHealthy ? matchScanLabel(label) : null
  const crop = link ? getCrop(link.cropId) : null

  function save() {
    addJournalEntry({
      date: todayISO(),
      type: 'scan',
      crop: cropForLabel(label) ?? '',
      title: `${label} (AI suggestion)`,
      notes: `${task === 'leaf' ? 'Disease scan' : task === 'pest' ? 'Pest scan' : 'Produce check'}. Model confidence ${confidence.toFixed(1)}%. Not a confirmed result.`,
      source: 'scan',
      aiSuggestion: true,
      confirmed: false,
    })
    setSaved(true)
  }

  return (
    <div className="space-y-2">
      {link && crop && onLearn && (
        <button
          onClick={() => onLearn(link.cropId, link.diseaseId, label)}
          className="tap w-full text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] rounded-2xl px-4 py-3"
        >
          <p className="text-sm font-bold text-[#2D6A4F]" style={display}>Learn about this possible disease</p>
          <p className="text-xs text-[#5A6A59]">Symptoms and prevention for {crop.name.toLowerCase()}. The scan is a suggestion, not a confirmed diagnosis.</p>
        </button>
      )}
      <button
        onClick={save}
        disabled={saved}
        className="tap w-full text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] disabled:opacity-70 rounded-2xl px-4 py-3"
      >
        <p className="text-sm font-bold text-[#2D6A4F]" style={display}>{saved ? 'Saved to Farm Journal' : 'Save to Farm Journal'}</p>
        <p className="text-xs text-[#5A6A59]">{saved ? 'Recorded as an unconfirmed AI suggestion in this browser.' : 'Keep this result as an unconfirmed note in this browser.'}</p>
      </button>
    </div>
  )
}
