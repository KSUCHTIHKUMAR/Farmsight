import { useSyncExternalStore } from 'react'

function probe() {
  try {
    localStorage.setItem('__fs_probe', '1')
    localStorage.removeItem('__fs_probe')
    return true
  } catch {
    return false
  }
}

// True only if this browser lets us write to localStorage. Data is never synced to a server.
export const storageAvailable = probe()

const cache = new Map<string, unknown>()
const listeners = new Set<() => void>()

function get<T>(key: string, init: T): T {
  if (cache.has(key)) return cache.get(key) as T
  let v: T = init
  if (storageAvailable) {
    try {
      const raw = localStorage.getItem(key)
      if (raw) v = JSON.parse(raw) as T
    } catch {
      v = init
    }
  }
  cache.set(key, v)
  return v
}

function set<T>(key: string, v: T) {
  cache.set(key, v)
  if (storageAvailable) {
    try {
      localStorage.setItem(key, JSON.stringify(v))
    } catch {
      /* quota or privacy mode; value stays in memory for this session */
    }
  }
  listeners.forEach((l) => l())
}

function subscribe(l: () => void) {
  listeners.add(l)
  return () => {
    listeners.delete(l)
  }
}

export function useStored<T>(key: string, init: T): [T, (u: T | ((p: T) => T)) => void] {
  const value = useSyncExternalStore(subscribe, () => get(key, init))
  const update = (u: T | ((p: T) => T)) => set(key, typeof u === 'function' ? (u as (p: T) => T)(get(key, init)) : u)
  return [value, update]
}

export const JOURNAL_KEY = 'farmsight.journal.v1'
export const PLANS_KEY = 'farmsight.plans.v1'

export type JournalType = 'observation' | 'scan' | 'watering' | 'fertilizer' | 'harvest' | 'note'

export interface JournalEntry {
  id: string
  date: string
  type: JournalType
  crop: string
  title: string
  notes: string
  quantity?: number
  unit?: string
  source: 'manual' | 'scan' | 'demo'
  aiSuggestion?: boolean
  confirmed?: boolean
}

export const uid = () => Math.random().toString(36).slice(2, 10)

export function addJournalEntry(e: Omit<JournalEntry, 'id'>) {
  set(JOURNAL_KEY, [{ ...e, id: uid() }, ...get<JournalEntry[]>(JOURNAL_KEY, [])])
}
