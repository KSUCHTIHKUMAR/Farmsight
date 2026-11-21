import type { ReactNode } from 'react'
import { cropImg } from './crops'

export type ToolId = 'overview' | 'hub' | 'care' | 'calendar' | 'journal'

export const TOOLS: { id: ToolId; label: string; subtitle: string }[] = [
  { id: 'overview', label: 'Farm Overview', subtitle: 'Tasks and shortcuts' },
  { id: 'hub', label: 'Knowledge Hub', subtitle: 'Crop profiles and search' },
  { id: 'care', label: 'Crop Care Guide', subtitle: 'Soil, nutrients, prevention' },
  { id: 'calendar', label: 'Crop Calendar', subtitle: 'Stages and tasks' },
  { id: 'journal', label: 'Farm Journal', subtitle: 'Records and scan notes' },
]

export const display = { fontFamily: 'Manrope, sans-serif' } as const

export const inputCls =
  'w-full rounded-xl border border-[#DDD8CE] bg-white px-3 py-2.5 text-sm text-[#1A201A] focus:outline-none focus:ring-2 focus:ring-[#52B788]'

export function Card({ children, className = '', accent }: { children: ReactNode; className?: string; accent?: string }) {
  return (
    <div className={`bg-white border border-[#DDD8CE] rounded-2xl p-4 sm:p-5 ${className}`} style={accent ? { borderTop: `3px solid ${accent}` } : undefined}>
      {children}
    </div>
  )
}

export function CropThumb({ id, tint, size = 44 }: { id: string; tint: string; size?: number }) {
  return (
    <img
      src={cropImg(id, size * 3, size * 3)}
      alt=""
      loading="lazy"
      className="rounded-2xl object-cover flex-shrink-0"
      style={{ width: size, height: size, boxShadow: `0 0 0 2px #fff, 0 0 0 4px ${tint}55` }}
    />
  )
}

const TOOL_LOOK: Record<ToolId, { from: string; image: string }> = {
  overview: { from: '#2D6A4F', image: 'vineyard' },
  hub: { from: '#2D6A4F', image: 'vineyard' },
  care: { from: '#8A5A22', image: 'potato' },
  calendar: { from: '#2B6A8F', image: 'watermelon' },
  journal: { from: '#7A3F6B', image: 'grapes' },
}

export function ToolBanner({ tool, title, subtitle }: { tool: ToolId; title: string; subtitle: string }) {
  const look = TOOL_LOOK[tool]
  return (
    <div className="relative rounded-2xl overflow-hidden mb-4 min-h-[7rem] sm:min-h-[9rem] flex items-end">
      <img src={cropImg(look.image, 1000, 400)} alt="" className="absolute inset-0 w-full h-full object-cover" />
      <div className="absolute inset-0" style={{ background: `linear-gradient(100deg, ${look.from}F2 0%, ${look.from}B3 55%, ${look.from}26 100%)` }} />
      <div className="relative p-4 sm:p-6 text-white max-w-md">
        <h2 className="text-xl sm:text-2xl font-extrabold" style={display}>{title}</h2>
        <p className="text-xs sm:text-sm text-white/85 mt-1">{subtitle}</p>
      </div>
    </div>
  )
}

export function H({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-base sm:text-lg font-extrabold text-[#1A201A] mb-3" style={display}>
      {children}
    </h3>
  )
}

export function Note({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warn' }) {
  const cls = tone === 'warn' ? 'bg-[#FDE8D8] text-[#8A4A1C]' : 'bg-[#D8EFDF] text-[#1F4F3A]'
  return <p className={`${cls} rounded-xl px-4 py-3 text-xs leading-relaxed font-medium`}>{children}</p>
}

export function Pill({ children, color = '#2D6A4F', bg = '#D8EFDF' }: { children: ReactNode; color?: string; bg?: string }) {
  return (
    <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full whitespace-nowrap" style={{ color, backgroundColor: bg }}>
      {children}
    </span>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-[#3A4A38] mb-1">{label}</span>
      {children}
    </label>
  )
}

export function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className={`tap whitespace-nowrap text-sm font-semibold px-4 py-2 rounded-full border transition-colors duration-150 ${
        on ? 'bg-[#2D6A4F] text-white border-[#2D6A4F]' : 'bg-white text-[#3A4A38] border-[#DDD8CE] hover:border-[#52B788]'
      }`}
      style={display}
    >
      {children}
    </button>
  )
}

export function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc pl-5 text-sm text-[#3A4A38] space-y-1.5 leading-relaxed">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  )
}

export function Monogram({ name, tint, bg, size = 44 }: { name: string; tint: string; bg: string; size?: number }) {
  return (
    <div className="rounded-2xl flex items-center justify-center font-extrabold flex-shrink-0" style={{ width: size, height: size, color: tint, backgroundColor: bg, fontSize: size * 0.42, ...display }}>
      {name[0]}
    </div>
  )
}

export function ToolIcon({ id, color = 'currentColor', size = 16 }: { id: ToolId; color?: string; size?: number }) {
  const p = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: color, strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  if (id === 'hub') return <svg {...p}><path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2z" /><path d="M8 7h6M8 11h6" /></svg>
  if (id === 'care') return <svg {...p}><path d="M12 22V10" /><path d="M12 14c0-4-3-6-7-6 0 4 3 6 7 6zM12 12c0-4 3-6 7-6 0 4-3 6-7 6z" /></svg>
  if (id === 'calendar') return <svg {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></svg>
  if (id === 'journal') return <svg {...p}><path d="M5 3h12a2 2 0 0 1 2 2v16H7a2 2 0 0 1-2-2z" /><path d="M9 8h6M9 12h6" /></svg>
  return <svg {...p}><path d="M3 12l9-8 9 8" /><path d="M5 10v10h14V10" /></svg>
}
