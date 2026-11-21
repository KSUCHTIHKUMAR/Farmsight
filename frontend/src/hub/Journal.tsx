import { useState } from 'react'
import { CROPS, getCrop } from './crops'
import { todayISO, fmtDate } from './planner'
import { JOURNAL_KEY, storageAvailable, uid, useStored, type JournalEntry, type JournalType } from './store'
import { Card, Chip, CropThumb, Field, H, Note, Pill, display, inputCls } from './ui'

const TYPES: { id: JournalType; label: string }[] = [
  { id: 'observation', label: 'Observation' },
  { id: 'scan', label: 'Scan result' },
  { id: 'watering', label: 'Watering' },
  { id: 'fertilizer', label: 'Fertilizer' },
  { id: 'harvest', label: 'Harvest' },
  { id: 'note', label: 'Note' },
]

const DEMO: Omit<JournalEntry, 'id'>[] = [
  { date: todayISO(), type: 'observation', crop: 'tomato', title: 'Lower leaves yellowing', notes: 'Demonstration entry. Spots on 3 plants near the fence.', source: 'demo' },
  { date: todayISO(), type: 'watering', crop: 'tomato', title: 'Drip irrigation, morning', notes: 'Demonstration entry.', source: 'demo' },
  { date: todayISO(), type: 'harvest', crop: 'maize', title: 'First cobs picked', notes: 'Demonstration entry.', quantity: 3.5, unit: 'kg', source: 'demo' },
]

const label = (t: JournalType) => TYPES.find((x) => x.id === t)?.label ?? t

export default function Journal() {
  const [entries, setEntries] = useStored<JournalEntry[]>(JOURNAL_KEY, [])
  const [filter, setFilter] = useState<'all' | JournalType>('all')
  const [q, setQ] = useState('')
  const [f, setF] = useState({ date: todayISO(), type: 'observation' as JournalType, crop: 'tomato', title: '', notes: '', quantity: '', unit: 'kg' })

  const shown = entries
    .filter((e) => (filter === 'all' || e.type === filter) && (!q.trim() || `${e.title} ${e.notes} ${e.crop}`.toLowerCase().includes(q.trim().toLowerCase())))
    .sort((a, b) => b.date.localeCompare(a.date))

  function add() {
    if (!f.title.trim()) return
    const qty = f.quantity.trim() === '' ? undefined : Number(f.quantity)
    if (qty !== undefined && (!isFinite(qty) || qty < 0)) return
    setEntries((p) => [{ id: uid(), date: f.date, type: f.type, crop: f.crop, title: f.title.trim(), notes: f.notes.trim(), quantity: f.type === 'harvest' ? qty : undefined, unit: f.type === 'harvest' ? f.unit : undefined, source: 'manual' }, ...p])
    setF({ ...f, title: '', notes: '', quantity: '' })
  }

  const harvestTotals = Object.entries(
    entries.filter((e) => e.type === 'harvest' && e.quantity != null).reduce<Record<string, number>>((m, e) => {
      const k = `${e.crop}|${e.unit}`
      m[k] = (m[k] ?? 0) + (e.quantity ?? 0)
      return m
    }, {}),
  )

  return (
    <div className="space-y-4">
      <Note tone={storageAvailable ? 'info' : 'warn'}>
        {storageAvailable
          ? 'Entries are stored in this browser only (local storage). They are not uploaded, synced or backed up, and clearing site data will erase them.'
          : 'Local storage is unavailable here, so entries last only for this session and disappear on reload.'}
      </Note>

      <Card className="space-y-3">
        <H>New entry</H>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label="Date"><input type="date" className={inputCls} value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></Field>
          <Field label="Type">
            <select className={inputCls} value={f.type} onChange={(e) => setF({ ...f, type: e.target.value as JournalType })}>
              {TYPES.filter((t) => t.id !== 'scan').map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          </Field>
          <Field label="Crop">
            <select className={inputCls} value={f.crop} onChange={(e) => setF({ ...f, crop: e.target.value })}>
              {CROPS.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Title"><input className={inputCls} value={f.title} maxLength={80} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="What happened?" /></Field>
        {f.type === 'harvest' && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Quantity"><input className={inputCls} inputMode="decimal" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
            <Field label="Unit">
              <select className={inputCls} value={f.unit} onChange={(e) => setF({ ...f, unit: e.target.value })}>
                <option>kg</option><option>quintal</option><option>tonne</option><option>crates</option><option>pieces</option>
              </select>
            </Field>
          </div>
        )}
        <Field label="Notes"><textarea className={inputCls} rows={3} value={f.notes} maxLength={500} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
        <div className="flex flex-wrap gap-3">
          <button onClick={add} disabled={!f.title.trim()} className="tap bg-[#2D6A4F] text-white font-bold text-sm px-5 py-3 rounded-xl disabled:opacity-40" style={display}>Save entry</button>
          {entries.length === 0 && (
            <button onClick={() => setEntries(DEMO.map((d) => ({ ...d, id: uid() })))} className="tap text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-3 rounded-xl" style={display}>Load demonstration entries</button>
          )}
        </div>
      </Card>

      {harvestTotals.length > 0 && (
        <Card>
          <H>Harvest totals</H>
          <div className="flex flex-wrap gap-2">{harvestTotals.map(([k, v]) => { const [c, u] = k.split('|'); return <Pill key={k}>{getCrop(c)?.name ?? c}: {v} {u}</Pill> })}</div>
        </Card>
      )}

      <div className="space-y-3">
        <input type="search" aria-label="Search journal" className={inputCls} placeholder="Search entries" value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1" role="group" aria-label="Filter entries">
          <Chip on={filter === 'all'} onClick={() => setFilter('all')}>All</Chip>
          {TYPES.map((t) => <Chip key={t.id} on={filter === t.id} onClick={() => setFilter(t.id)}>{t.label}</Chip>)}
        </div>
        {shown.length === 0 ? (
          <Card><p className="text-sm text-[#5A6A59]">{entries.length === 0 ? 'No entries yet. Add one above, or save a scan result from the Results screen.' : 'No entries match.'}</p></Card>
        ) : (
          <ul className="space-y-2" aria-live="polite">
            {shown.map((e) => (
              <li key={e.id} className="bg-white border border-[#DDD8CE] rounded-2xl p-4 flex gap-3" style={{ borderLeft: `4px solid ${getCrop(e.crop)?.tint ?? '#52B788'}` }}>
                {getCrop(e.crop) && <CropThumb id={e.crop} tint={getCrop(e.crop)!.tint} size={48} />}
                <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <Pill>{label(e.type)}</Pill>
                  <span className="text-xs text-[#5A6A59]">{fmtDate(e.date)} · {getCrop(e.crop)?.name ?? e.crop}</span>
                  {e.source === 'demo' && <Pill color="#8A4A1C" bg="#FDE8D8">Demonstration</Pill>}
                  {e.aiSuggestion && (e.confirmed ? <Pill>Confirmed by you</Pill> : <Pill color="#8A4A1C" bg="#FDE8D8">AI suggestion, unconfirmed</Pill>)}
                </div>
                <p className="text-sm font-bold text-[#1A201A]" style={display}>{e.title}</p>
                {e.quantity != null && <p className="text-sm text-[#3A4A38]">{e.quantity} {e.unit}</p>}
                {e.notes && <p className="text-sm text-[#3A4A38] mt-1">{e.notes}</p>}
                <div className="flex gap-4 mt-2">
                  {e.aiSuggestion && (
                    <button onClick={() => setEntries((p) => p.map((x) => (x.id === e.id ? { ...x, confirmed: !x.confirmed } : x)))} className="text-xs font-semibold text-[#2D6A4F]">
                      {e.confirmed ? 'Mark as unconfirmed' : 'I have confirmed this'}
                    </button>
                  )}
                  <button onClick={() => setEntries((p) => p.filter((x) => x.id !== e.id))} className="text-xs font-semibold text-[#C83232]">Delete</button>
                </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
