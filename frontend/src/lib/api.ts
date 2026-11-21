export type Task = 'leaf' | 'produce' | 'pest'

export interface TopGuess {
  label: string
  name: string
  prob: number
}

export interface AnalyseResult {
  task: Task
  confident: boolean
  top: TopGuess[]
  fruit?: { name: string; prob: number }
  state?: { name: 'fresh' | 'rotten'; prob: number }
  advice?: string | null
  source?: string | null
  disclaimer?: string
  crop_supported?: boolean
  disease_supported?: boolean
  selected_crop?: string
  crop_probability?: number
  not_target?: boolean
  images: { photo: string; heatmap: string }
  model_info: { clean_accuracy?: number; field_accuracy?: number; note: string }
}

export type AnalyseErrorKind = 'empty' | 'tooLarge' | 'unreadable' | 'network' | 'server'

export class AnalyseError extends Error {
  kind: AnalyseErrorKind
  constructor(kind: AnalyseErrorKind, message?: string) {
    super(message ?? kind)
    this.kind = kind
  }
}

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

/** Probabilities may arrive as 0–1 fractions or 0–100 percentages; this only normalises for display. */
export function pct(p: number): number {
  return p <= 1 ? p * 100 : p
}

export function fmtPct(p: number): string {
  return `${Math.round(pct(p))}%`
}

export function isHealthyName(s: string): boolean {
  return /healthy|no pest|not.*pest/i.test(s)
}

const ENDPOINT = (import.meta.env.VITE_FARMSIGHT_API_URL ?? '').trim().replace(/\/+$/, '')

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function finiteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function adaptResult(value: unknown, task: Task): AnalyseResult | null {
  if (!isRecord(value) || value.task !== task || typeof value.confident !== 'boolean') return null
  if (
    !Array.isArray(value.top) ||
    !value.top.every(
      (guess) =>
        isRecord(guess) &&
        typeof guess.label === 'string' &&
        typeof guess.name === 'string' &&
        finiteNumber(guess.prob) &&
        guess.prob >= 0 &&
        guess.prob <= 1,
    )
  ) {
    return null
  }
  if (
    !isRecord(value.images) ||
    typeof value.images.photo !== 'string' ||
    typeof value.images.heatmap !== 'string' ||
    !isRecord(value.model_info) ||
    typeof value.model_info.note !== 'string'
  ) {
    return null
  }
  if (
    value.fruit !== undefined &&
    (!isRecord(value.fruit) ||
      typeof value.fruit.name !== 'string' ||
      !finiteNumber(value.fruit.prob))
  ) {
    return null
  }
  if (
    value.state !== undefined &&
    (!isRecord(value.state) ||
      (value.state.name !== 'fresh' && value.state.name !== 'rotten') ||
      !finiteNumber(value.state.prob))
  ) {
    return null
  }

  const cleanAccuracy = finiteNumber(value.model_info.clean_accuracy)
    ? value.model_info.clean_accuracy
    : undefined
  const fieldAccuracy = finiteNumber(value.model_info.field_accuracy)
    ? value.model_info.field_accuracy
    : undefined

  return {
    task,
    confident: value.confident,
    top: value.top as TopGuess[],
    fruit: value.fruit as AnalyseResult['fruit'],
    state: value.state as AnalyseResult['state'],
    advice: typeof value.advice === 'string' || value.advice === null ? value.advice : undefined,
    source: typeof value.source === 'string' || value.source === null ? value.source : undefined,
    disclaimer: typeof value.disclaimer === 'string' ? value.disclaimer : undefined,
    crop_supported: typeof value.crop_supported === 'boolean' ? value.crop_supported : undefined,
    disease_supported:
      typeof value.disease_supported === 'boolean' ? value.disease_supported : undefined,
    selected_crop: typeof value.selected_crop === 'string' ? value.selected_crop : undefined,
    crop_probability: finiteNumber(value.crop_probability) ? value.crop_probability : undefined,
    not_target: typeof value.not_target === 'boolean' ? value.not_target : undefined,
    images: {
      photo: value.images.photo,
      heatmap: value.images.heatmap,
    },
    model_info: {
      clean_accuracy: cleanAccuracy,
      field_accuracy: fieldAccuracy,
      note: value.model_info.note,
    },
  }
}

export async function analyse(task: Task, file: File | null | undefined): Promise<AnalyseResult> {
  if (!file || file.size === 0) throw new AnalyseError('empty')
  if (file.size > MAX_UPLOAD_BYTES) throw new AnalyseError('tooLarge')
  if (file.type && !file.type.startsWith('image/')) throw new AnalyseError('unreadable')

  const body = new FormData()
  body.append('task', task)
  body.append('file', file)

  let response: Response
  try {
    response = await fetch(`${ENDPOINT}/api/analyse`, { method: 'POST', body })
  } catch {
    throw new AnalyseError('network')
  }
  if (response.status === 413) throw new AnalyseError('tooLarge')
  if (response.status === 400 || response.status === 415 || response.status === 422) {
    throw new AnalyseError('unreadable')
  }
  if (!response.ok) throw new AnalyseError('server')

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    throw new AnalyseError('server', 'The analysis service returned invalid JSON.')
  }
  const result = adaptResult(payload, task)
  if (!result) throw new AnalyseError('server', 'Unexpected response shape')
  if (result.top.length === 0) throw new AnalyseError('empty')
  return result
}
