import { useMemo, useState } from 'react'
import { ABOUT_TIMINGS, CROPS, getCrop, type Priority } from './crops'
import { addDays, daysBetween, flattenPlan, fmtDate, todayISO, type FlatTask, type Plan } from './planner'
import { PLANS_KEY, storageAvailable, uid, useStored } from './store'
import { Card, Chip, CropThumb, Field, H, Note, Pill, display, inputCls } from './ui'

const PRI: Record<Priority, { label: string; color: string; bg: string }> = {
  high: { label: 'High', color: '#C83232', bg: '#FCE4E4' },
  medium: { label: 'Medium', color: '#8A4A1C', bg: '#FDE8D8' },
  low: { label: 'Low', color: '#2D6A4F', bg: '#D8EFDF' },
}

type Status = 'all' | 'pending' | 'overdue' | 'done'

export default function CalendarView({ initialCrop }: { initialCrop?: string }) {
  const [plans, setPlans] = useStored<Plan[]>(PLANS_KEY, [])
  const [cropId, setCropId] = useState(initialCrop ?? 'tomato')
  const [date, setDate] = useState(todayISO())
  const [activeId, setActiveId] = useState<string | null>(plans[0]?.id ?? null)
  const [status, setStatus] = useState<Status>('all')
  const [prio, setPrio] = useState<'all' | Priority>('all')
  const [nt, setNt] = useState({ title: '', due: todayISO(), priority: 'medium' as Priority })

  const plan = plans.find((p) => p.id === activeId) ?? null
  const crop = plan ? getCrop(plan.cropId) : undefined
  const today = todayISO()

  const tasks = useMemo(() => (plan && crop ? flattenPlan(plan, crop) : []), [plan, crop])
  const shown = tasks.filter((t) => {
    const overdue = !t.done && t.due < today
    if (status === 'pending' && t.done) return false
    if (status === 'done' && !t.done) return false
    if (status === 'overdue' && !overdue) return false
    return prio === 'all' || t.priority === prio
  })
  const doneCount = tasks.filter((t) => t.done).length

  function createPlan() {
    if (!date) return
    const p: Plan = { id: uid(), cropId, planting: date, done: {}, moved: {}, custom: [], customDone: {} }
    setPlans((prev) => [...prev, p])
    setActiveId(p.id)
  }
  function patch(fn: (p: Plan) => Plan) {
    setPlans((prev) => prev.map((p) => (p.id === activeId ? fn(p) : p)))
  }
  function toggle(t: FlatTask) {
    patch((p) => (t.custom ? { ...p, customDone: { ...p.customDone, [t.key]: !t.done } } : { ...p, done: { ...p.done, [t.key]: !t.done } }))
  }
  function move(t: FlatTask, due: string) {
    if (!due) return
    patch((p) => (t.custom ? { ...p, custom: p.custom.map((c) => (c.id === t.key ? { ...c, due } : c)) } : { ...p, moved: { ...p.moved, [t.key]: due } }))
  }
  function addCustom() {
    if (!nt.title.trim() || !nt.due) return
    patch((p) => ({ ...p, custom: [...p.custom, { id: uid(), title: nt.title.trim(), due: nt.due, priority: nt.priority }] }))
    setNt({ ...nt, title: '' })
  }
  function removePlan() {
    setPlans((prev) => prev.filter((p) => p.id !== activeId))
    setActiveId(null)
  }

  return (
    <div className="space-y-4">
      <Note tone="warn">{ABOUT_TIMINGS} Treat every date here as a suggestion to adjust to your own field.</Note>

      <Card className="space-y-3">
        <H>New plan</H>
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-3 items-end">
          <Field label="Crop">
            <select className={inputCls} value={cropId} onChange={(e) => setCropId(e.target.value)}>
              {CROPS.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label={getCrop(cropId)?.plan.start ?? 'Planting date'}>
            <input type="date" className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
          <button onClick={createPlan} disabled={!date} className="tap bg-[#2D6A4F] text-white font-bold text-sm px-5 py-3 rounded-xl hover:bg-[#235a41] disabled:opacity-40" style={display}>
            Create plan
          </button>
        </div>
        <p className="text-xs text-[#5A6A59]">{storageAvailable ? 'Plans are saved in this browser only (local storage). They are not synced or backed up.' : 'Local storage is unavailable here, so plans last only until you close or reload this page.'}</p>
      </Card>

      {plans.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1" role="group" aria-label="Your plans">
          {plans.map((p) => <Chip key={p.id} on={p.id === activeId} onClick={() => setActiveId(p.id)}>{getCrop(p.cropId)?.name} · {fmtDate(p.planting)}</Chip>)}
        </div>
      )}

      {plan && crop ? (
        <div className="space-y-4 animate-fade-in" key={plan.id}>
          <Card accent={crop.tint}>
            <div className="flex items-center gap-3 mb-4 rounded-xl p-2" style={{ backgroundColor: crop.tintBg }}>
              <CropThumb id={crop.id} tint={crop.tint} size={52} />
              <div>
                <p className="font-extrabold" style={{ ...display, color: crop.tint }}>{crop.name}</p>
                <p className="text-xs text-[#3A4A38]">{crop.plan.start}: {fmtDate(plan.planting)}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <H>Estimated growth stages</H>
              <button onClick={removePlan} className="text-xs font-semibold text-[#C83232]">Delete plan</button>
            </div>
            <ol className="space-y-2">
              {crop.stages.map((s) => {
                const from = fmtDate(addDays(plan.planting, s.from))
                const to = fmtDate(addDays(plan.planting, s.to))
                const nowDay = daysBetween(plan.planting, today)
                const current = nowDay >= s.from && nowDay < s.to
                return (
                  <li key={s.name} className={`rounded-xl px-3 py-2 border text-sm ${current ? 'border-[#52B788] bg-[#F3FAF5]' : 'border-[#EEEAE1]'}`}>
                    <div className="flex flex-wrap justify-between gap-1">
                      <span className="font-bold text-[#1A201A]" style={display}>{s.name}{current && <span className="ml-2 text-xs font-semibold text-[#2D6A4F]">current estimate</span>}</span>
                      <span className="text-xs text-[#5A6A59]">about {from} to {to}</span>
                    </div>
                    <p className="text-xs text-[#5A6A59]">{s.note}</p>
                  </li>
                )
              })}
            </ol>
            {crop.plan.harvestNote && <p className="text-xs text-[#5A6A59] mt-3">{crop.plan.harvestNote}</p>}
          </Card>

          <Card accent="#2B6A8F">
            <div className="flex items-center justify-between mb-3 gap-2">
              <H>Tasks</H>
              <Pill>{doneCount} of {tasks.length} done</Pill>
            </div>
            <div className="h-2 rounded-full bg-[#E8E4DB] overflow-hidden mb-3" aria-hidden>
              <div className="h-full bg-[#52B788] transition-all duration-300" style={{ width: `${tasks.length ? (doneCount / tasks.length) * 100 : 0}%` }} />
            </div>
            <div className="flex flex-wrap gap-2 mb-2" role="group" aria-label="Filter by status">
              {(['all', 'pending', 'overdue', 'done'] as Status[]).map((s) => <Chip key={s} on={status === s} onClick={() => setStatus(s)}>{s[0].toUpperCase() + s.slice(1)}</Chip>)}
            </div>
            <div className="flex flex-wrap gap-2 mb-4" role="group" aria-label="Filter by priority">
              {(['all', 'high', 'medium', 'low'] as const).map((s) => <Chip key={s} on={prio === s} onClick={() => setPrio(s)}>{s === 'all' ? 'Any priority' : PRI[s].label}</Chip>)}
            </div>
            {shown.length === 0 ? (
              <p className="text-sm text-[#5A6A59]">No tasks match these filters.</p>
            ) : (
              <ul className="space-y-2" aria-live="polite">
                {shown.map((t) => {
                  const overdue = !t.done && t.due < today
                  return (
                    <li key={t.key} className={`rounded-xl border p-3 flex gap-3 ${t.done ? 'bg-[#F5F2EC] border-[#EEEAE1]' : overdue ? 'border-[#F2B8B8] bg-[#FFF7F7]' : 'border-[#DDD8CE]'}`}>
                      <input type="checkbox" checked={t.done} onChange={() => toggle(t)} aria-label={`Mark ${t.title} done`} className="mt-1 w-5 h-5 accent-[#2D6A4F] flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-semibold ${t.done ? 'line-through text-[#5A6A59]' : 'text-[#1A201A]'}`} style={display}>{t.title}</p>
                        <p className="text-xs text-[#5A6A59] mt-0.5">{t.detail}</p>
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <Pill color={PRI[t.priority].color} bg={PRI[t.priority].bg}>{PRI[t.priority].label}</Pill>
                          {overdue && <Pill color="#C83232" bg="#FCE4E4">Overdue</Pill>}
                          <label className="flex items-center gap-1 text-xs text-[#5A6A59]">
                            Due
                            <input type="date" value={t.due} onChange={(e) => move(t, e.target.value)} className="rounded-lg border border-[#DDD8CE] px-2 py-1 text-xs text-[#1A201A]" />
                          </label>
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>

          <Card>
            <H>Add your own task</H>
            <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto_auto] gap-3 items-end">
              <Field label="Task"><input className={inputCls} value={nt.title} maxLength={80} onChange={(e) => setNt({ ...nt, title: e.target.value })} placeholder="e.g. Repair drip line" /></Field>
              <Field label="Due"><input type="date" className={inputCls} value={nt.due} onChange={(e) => setNt({ ...nt, due: e.target.value })} /></Field>
              <Field label="Priority">
                <select className={inputCls} value={nt.priority} onChange={(e) => setNt({ ...nt, priority: e.target.value as Priority })}>
                  <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                </select>
              </Field>
              <button onClick={addCustom} disabled={!nt.title.trim()} className="tap bg-[#2D6A4F] text-white font-bold text-sm px-5 py-3 rounded-xl disabled:opacity-40" style={display}>Add</button>
            </div>
          </Card>
        </div>
      ) : (
        <Card><p className="text-sm text-[#5A6A59]">No plan selected. Create one above to see stages and tasks.</p></Card>
      )}
    </div>
  )
}
