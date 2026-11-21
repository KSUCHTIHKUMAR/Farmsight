import type { Crop, Priority, TaskKind } from './crops'

export interface PlanTask {
  key: string
  title: string
  detail: string
  due: string
  priority: Priority
  kind: TaskKind
  stage?: string
}

export interface CustomTask {
  id: string
  title: string
  due: string
  priority: Priority
}

export interface Plan {
  id: string
  cropId: string
  planting: string
  done: Record<string, boolean>
  moved: Record<string, string>
  custom: CustomTask[]
  customDone: Record<string, boolean>
}

export function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function addDays(iso: string, days: number) {
  const [y, m, d] = iso.split('-').map(Number)
  const t = new Date(Date.UTC(y, m - 1, d + Math.round(days)))
  return t.toISOString().slice(0, 10)
}

export function fmtDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
}

export function daysBetween(a: string, b: string) {
  const f = (s: string) => {
    const [y, m, d] = s.split('-').map(Number)
    return Date.UTC(y, m - 1, d)
  }
  return Math.round((f(b) - f(a)) / 86400000)
}

function series(from: number, to: number, every: number, maxCount = 12) {
  const span = Math.max(to - from, 0)
  const step = Math.max(every, Math.ceil(span / maxCount) || every)
  const days: number[] = []
  for (let d = from; d < to; d += step) days.push(d)
  return days
}

export function stageAt(crop: Crop, day: number) {
  return crop.stages.find((s) => day >= s.from && day < s.to)?.name
}

export function buildTasks(crop: Crop, planting: string): PlanTask[] {
  const p = crop.plan
  const out: PlanTask[] = []
  const add = (key: string, title: string, detail: string, day: number, priority: Priority, kind: TaskKind) =>
    out.push({ key, title, detail, due: addDays(planting, day), priority, kind, stage: stageAt(crop, Math.max(day, 0)) })

  const fieldStart = p.nursery ? p.nursery.transplantDay : 0
  add('soil-test', 'Consider a soil test and prepare the plot', 'A soil test guides liming and fertilizer decisions. Ask your local extension service how to sample.', -14, 'high', 'nutrient')
  add('sow', p.start, p.nursery ? 'Day one of the nursery. Use healthy, clean seed or planting material.' : 'Use healthy, clean planting material suited to your region.', 0, 'high', 'sow')
  if (p.nursery) {
    add('harden', 'Harden off seedlings', 'Gradually expose seedlings to field conditions before transplanting.', p.nursery.transplantDay - 5, 'medium', 'transplant')
    add('transplant', 'Transplant seedlings to the field', 'Transplant when seedlings are sturdy; water in well.', p.nursery.transplantDay, 'high', 'transplant')
  }
  series(fieldStart, p.horizon, p.irrigEvery).forEach((d, i) =>
    add(`irr-${i}`, 'Irrigation check', 'Check soil moisture at root depth and water as the crop and weather require.', d + 2, 'medium', 'irrigation'))
  series(fieldStart + 7, Math.min(p.horizon, p.harvestFrom < 9999 ? p.harvestFrom * 0.7 : p.horizon), p.weedEvery).forEach((d, i) =>
    add(`weed-${i}`, 'Weeding', 'Remove weeds that compete for light, water and nutrients or harbour pests.', d, 'low', 'weeding'))
  series(fieldStart + 10, p.horizon, p.nutrientEvery).forEach((d, i) =>
    add(`nut-${i}`, 'Nutrient monitoring', 'Check leaf colour and growth against soil test results. Adjust only on local advice.', d, 'medium', 'nutrient'))
  series(fieldStart + 5, p.horizon, p.scoutEvery).forEach((d, i) =>
    add(`scout-${i}`, 'Disease and pest scouting', 'Inspect leaves, stems and fruit. AI scan results are only suggestions until confirmed.', d, 'high', 'scouting'))
  ;(p.extra ?? []).forEach((t) => add(t.key, t.title, t.detail, t.day, t.priority, t.kind))
  if (p.harvestFrom < 9999) {
    add('harvest-prep', 'Prepare for harvest', 'Clean tools and containers, and review the maturity indicators for this crop.', p.harvestFrom - 7, 'medium', 'harvest')
    add('harvest', 'Begin harvest checks', crop.harvest[0], p.harvestFrom, 'high', 'harvest')
  }
  return out.sort((a, b) => a.due.localeCompare(b.due))
}

export interface FlatTask {
  planId: string
  cropId: string
  key: string
  custom: boolean
  title: string
  detail: string
  due: string
  priority: Priority
  kind: TaskKind
  done: boolean
}

export function flattenPlan(plan: Plan, crop: Crop): FlatTask[] {
  const generated = buildTasks(crop, plan.planting).map<FlatTask>((t) => ({
    planId: plan.id, cropId: plan.cropId, key: t.key, custom: false, title: t.title, detail: t.detail,
    due: plan.moved[t.key] ?? t.due, priority: t.priority, kind: t.kind, done: !!plan.done[t.key],
  }))
  const custom = plan.custom.map<FlatTask>((c) => ({
    planId: plan.id, cropId: plan.cropId, key: c.id, custom: true, title: c.title, detail: 'Your own task.',
    due: c.due, priority: c.priority, kind: 'other', done: !!plan.customDone[c.id],
  }))
  return [...generated, ...custom].sort((a, b) => a.due.localeCompare(b.due))
}
