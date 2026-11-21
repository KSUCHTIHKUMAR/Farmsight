import { useMemo } from 'react'
import { CROPS, cropImg, getCrop } from './crops'
import { flattenPlan, fmtDate, todayISO, type Plan } from './planner'
import { PLANS_KEY, useStored } from './store'
import { Card, H, Pill, ToolIcon, display, type ToolId } from './ui'

export default function Overview({ onTool, onScan }: { onTool: (t: ToolId, cropId?: string) => void; onScan?: (t: 'leaf' | 'produce' | 'pest') => void }) {
  const [plans] = useStored<Plan[]>(PLANS_KEY, [])
  const today = todayISO()
  const upcoming = useMemo(
    () =>
      plans
        .flatMap((p) => { const c = getCrop(p.cropId); return c ? flattenPlan(p, c) : [] })
        .filter((t) => !t.done)
        .sort((a, b) => a.due.localeCompare(b.due))
        .slice(0, 4),
    [plans],
  )
  const shortcuts = ['tomato', 'potato', 'mango', 'banana'].map((id) => CROPS.find((c) => c.id === id)!)

  return (
    <div className="space-y-4">
      {onScan && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button onClick={() => onScan('leaf')} className="card-lift text-left bg-[#2D6A4F] text-white rounded-2xl p-5">
            <p className="text-lg font-extrabold" style={display}>Diagnose Leaf</p>
            <p className="text-sm text-white/75">Scan leaves from 12 crops for disease.</p>
          </button>
          <button onClick={() => onScan('produce')} className="card-lift text-left bg-[#E07B39] text-white rounded-2xl p-5">
            <p className="text-lg font-extrabold" style={display}>Grade Produce</p>
            <p className="text-sm text-white/80">Grade 14 kinds of produce for freshness.</p>
          </button>
          <button onClick={() => onScan('pest')} className="card-lift text-left bg-[#8A4A1C] text-white rounded-2xl p-5 sm:col-span-2">
            <p className="text-lg font-extrabold" style={display}>Identify Pest</p>
            <p className="text-sm text-white/80">Identify common tomato pests from a close-up photo.</p>
          </button>
        </div>
      )}
      <button onClick={() => onTool('hub')} className="card-lift w-full text-left bg-white border-2 border-[#DDD8CE] hover:border-[#52B788] rounded-2xl p-4 flex items-center gap-3">
        <img src={cropImg('vineyard', 120, 120)} alt="" className="w-11 h-11 rounded-xl object-cover" />
        <div className="flex-1">
          <p className="font-bold text-[#1A201A]" style={display}>Knowledge Hub</p>
          <p className="text-xs text-[#5A6A59]">Search 19 fruit, vegetable and field crop profiles.</p>
        </div>
      </button>

      <Card accent="#2B6A8F">
        <div className="flex items-center justify-between mb-3">
          <H>Upcoming crop tasks</H>
          <button onClick={() => onTool('calendar')} className="text-xs font-semibold text-[#2B6A8F]">Open calendar</button>
        </div>
        {upcoming.length === 0 ? (
          <p className="text-sm text-[#5A6A59]">No tasks yet. Create a crop plan in the Crop Calendar to see what is due next.</p>
        ) : (
          <ul className="space-y-2">
            {upcoming.map((t) => (
              <li key={`${t.planId}-${t.key}`} className="flex items-center justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-[#1A201A]"><span className="font-semibold">{getCrop(t.cropId)?.name}</span> · {t.title}</span>
                {t.due < today ? <Pill color="#C83232" bg="#FCE4E4">Overdue</Pill> : <span className="text-xs text-[#5A6A59] whitespace-nowrap">{fmtDate(t.due)}</span>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card accent="#52B788">
        <H>Learn and record</H>
        <div className="grid grid-cols-2 gap-2">
          {shortcuts.map((c) => (
            <button key={c.id} onClick={() => onTool('hub', c.id)} className="tap flex items-center gap-2 text-left rounded-xl p-1.5 pr-3 text-sm font-semibold" style={{ backgroundColor: c.tintBg, color: c.tint, ...display }}>
              <img src={cropImg(c.id, 120, 120)} alt="" className="w-9 h-9 rounded-lg object-cover" />
              {c.name}
            </button>
          ))}
          <button onClick={() => onTool('care')} className="tap flex items-center gap-2 text-left rounded-xl px-3 py-2.5 text-sm font-semibold bg-[#F3E6D3] text-[#8A5A22]" style={display}><ToolIcon id="care" />Crop Care Guide</button>
          <button onClick={() => onTool('journal')} className="tap flex items-center gap-2 text-left rounded-xl px-3 py-2.5 text-sm font-semibold bg-[#EEDDF2] text-[#7A3F6B]" style={display}><ToolIcon id="journal" />Farm Journal</button>
        </div>
      </Card>
    </div>
  )
}
