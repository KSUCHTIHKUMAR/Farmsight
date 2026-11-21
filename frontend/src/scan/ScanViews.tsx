import { useEffect, useRef, useState, type ReactNode } from 'react'
import ScanFollowUp from '../hub/ScanFollowUp'
import { AnalyseError, fmtPct, isHealthyName, pct, type AnalyseResult, type Task } from '../lib/api'
import { useT } from '../lib/i18n'

const display = { fontFamily: 'Manrope, sans-serif' }
const MUTED = '#5A6A59'

type Tone = 'good' | 'bad' | 'warn' | 'unsure'
const TONES: Record<Tone, { fg: string; bg: string; bar: string }> = {
  good: { fg: '#1F5A41', bg: '#D8EFDF', bar: '#2D6A4F' },
  bad: { fg: '#A81F1F', bg: '#FCE4E4', bar: '#C83232' },
  warn: { fg: '#8A4B00', bg: '#FFEFD2', bar: '#D9822B' },
  unsure: { fg: '#8A4B00', bg: '#FFEFD2', bar: '#D9822B' },
}

// ── Small icons ──────────────────────────────────────────────────────────────

function Svg({ children, size = 20, color = 'currentColor' }: { children: ReactNode; size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="flex-shrink-0">
      {children}
    </svg>
  )
}
const CameraI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
    <circle cx="12" cy="13" r="4" />
  </Svg>
)
const UploadI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
  </Svg>
)
const CheckI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M8 12l3 3 5-6" />
  </Svg>
)
const AlertI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01" />
  </Svg>
)
const RetryI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <path d="M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15" />
  </Svg>
)
const LeafI = (p: { size?: number; color?: string }) => (
  <Svg {...p}>
    <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10zM2 21c0-3 1.9-5.5 6-7" />
  </Svg>
)

const primaryBtn =
  'w-full flex items-center justify-center gap-2.5 bg-[#2D6A4F] text-white font-bold text-base min-h-14 py-3.5 rounded-2xl hover:bg-[#235a41] tap'
const secondaryBtn =
  'w-full flex items-center justify-center gap-2.5 bg-white border-2 border-[#2D6A4F] text-[#2D6A4F] font-bold text-base min-h-14 py-3.5 rounded-2xl hover:bg-[#F5F2EC] tap'

// ── Camera ───────────────────────────────────────────────────────────────────

function CameraCapture({ task, onCapture, onClose, onUpload }: { task: Task; onCapture: (f: File) => void; onClose: () => void; onUpload: () => void }) {
  const { t } = useT()
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [status, setStatus] = useState<'starting' | 'live' | 'unavailable'>('starting')

  useEffect(() => {
    let cancelled = false
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus('unavailable')
      return
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((tr) => tr.stop())
          return
        }
        streamRef.current = s
        const v = videoRef.current
        if (v) {
          v.srcObject = s
          v.play().catch(() => {})
        }
        setStatus('live')
      })
      .catch(() => {
        if (!cancelled) setStatus('unavailable')
      })
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((tr) => tr.stop())
    }
  }, [])

  function shoot() {
    const v = videoRef.current
    if (!v || !v.videoWidth) return
    const c = document.createElement('canvas')
    c.width = v.videoWidth
    c.height = v.videoHeight
    c.getContext('2d')?.drawImage(v, 0, 0)
    c.toBlob(
      (b) => {
        if (b) onCapture(new File([b], 'capture.jpg', { type: 'image/jpeg' }))
      },
      'image/jpeg',
      0.92
    )
  }

  const tips = [task === 'leaf' ? t('camTipLeaf') : task === 'pest' ? t('camTipPest') : t('camTipFruit'), t('camTipLight')]
  const corner = 'absolute w-7 h-7 border-white'

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="relative rounded-2xl overflow-hidden bg-[#101510] mx-auto" style={{ aspectRatio: '3/4', maxHeight: '68dvh' }}>
        <video ref={videoRef} playsInline muted aria-label={t('takePhoto')} className={`absolute inset-0 w-full h-full object-cover ${status === 'live' ? '' : 'invisible'}`} />
        {status === 'live' && (
          <>
            <div className="absolute inset-[12%] rounded-3xl pointer-events-none" style={{ boxShadow: '0 0 0 999px rgba(10,16,10,0.5)' }} aria-hidden="true">
              <span className={`${corner} top-0 left-0 border-t-4 border-l-4 rounded-tl-3xl`} />
              <span className={`${corner} top-0 right-0 border-t-4 border-r-4 rounded-tr-3xl`} />
              <span className={`${corner} bottom-0 left-0 border-b-4 border-l-4 rounded-bl-3xl`} />
              <span className={`${corner} bottom-0 right-0 border-b-4 border-r-4 rounded-br-3xl`} />
            </div>
            <p className="absolute top-3 inset-x-3 text-center text-xs font-semibold text-white bg-black/55 rounded-full py-1.5 px-3 mx-auto w-fit max-w-full">{t('camGuide')}</p>
            <p className="absolute bottom-3 inset-x-3 text-center text-sm font-bold text-white mx-auto w-fit max-w-full bg-[#2D6A4F] rounded-full py-1.5 px-4" style={display}>
              {tips[0]}
            </p>
          </>
        )}
        {status === 'starting' && (
          <p role="status" className="absolute inset-0 flex items-center justify-center text-sm text-white/90">
            {t('camStarting')}
          </p>
        )}
        {status === 'unavailable' && (
          <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center">
            <CameraI size={32} color="#fff" />
            <p className="text-sm text-white leading-relaxed">{t('camUnavailable')}</p>
            <button onClick={onUpload} className="bg-white text-[#1F5A41] font-bold text-sm min-h-11 px-5 rounded-xl tap" style={display}>
              {t('camUseUpload')}
            </button>
          </div>
        )}
      </div>

      <ul className="bg-[#D8EFDF] rounded-xl px-4 py-3 space-y-1.5">
        {tips.map((tip) => (
          <li key={tip} className="flex items-center gap-2 text-sm font-medium text-[#1F5A41]">
            <CheckI size={16} color="#1F5A41" />
            {tip}
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between gap-4 pt-1">
        <button onClick={onClose} className="min-h-12 px-5 rounded-xl text-sm font-bold text-[#2D4A3A] bg-[#E8E4DB] hover:bg-[#DDD8CE] tap" style={display}>
          {t('cancel')}
        </button>
        <button
          onClick={shoot}
          disabled={status !== 'live'}
          aria-label={t('capture')}
          className="w-[72px] h-[72px] rounded-full bg-white border-[5px] border-[#2D6A4F] flex items-center justify-center disabled:opacity-40 tap"
        >
          <span className="w-12 h-12 rounded-full bg-[#2D6A4F]" />
        </button>
        <span className="w-[76px]" aria-hidden="true" />
      </div>
    </div>
  )
}

// ── Input ────────────────────────────────────────────────────────────────────

export function InputMethodContent({ task, onCapture }: { task: Task; onCapture: (file: File) => void }) {
  const { t } = useT()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [cameraOpen, setCameraOpen] = useState(false)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) onCapture(file)
  }

  const fileInput = <input ref={fileInputRef} type="file" accept="image/*" className="hidden" tabIndex={-1} onChange={handleFile} />

  if (cameraOpen) {
    return (
      <>
        <CameraCapture
          task={task}
          onCapture={onCapture}
          onClose={() => setCameraOpen(false)}
          onUpload={() => {
            setCameraOpen(false)
            setTimeout(() => fileInputRef.current?.click(), 0)
          }}
        />
        {fileInput}
      </>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-extrabold text-[#1A201A] mb-1.5" style={display}>
          {t('addPhoto')}
        </h2>
        <p className="text-sm leading-relaxed" style={{ color: MUTED }}>
          {task === 'leaf' ? t('tipLeaf') : task === 'pest' ? t('tipPest') : t('tipProduce')}
        </p>
      </div>

      <div className="relative rounded-2xl overflow-hidden bg-[#E8E4DB]" style={{ aspectRatio: '4/3' }}>
        <img
          src={
            task === 'leaf'
              ? 'https://images.unsplash.com/photo-1642307321395-b72347cbe944?w=700&h=525&fit=crop&auto=format'
              : task === 'pest'
                ? 'https://images.unsplash.com/photo-1631739196439-5eac4cc2dc6d?w=700&h=525&fit=crop&auto=format'
                : 'https://images.unsplash.com/photo-1707734534246-b456bdb7db6c?w=700&h=525&fit=crop&auto=format'
          }
          alt={task === 'leaf' ? 'Example of a leaf photo' : task === 'pest' ? 'Example of a pest photo' : 'Example of a fruit photo'}
          className="w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 flex items-center justify-center p-4">
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl px-4 py-3 flex items-center gap-2.5">
            <CameraI size={18} color="#2D6A4F" />
            <span className="text-sm font-semibold text-[#1F5A41]" style={display}>
              {t('photoHere')}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-[#D8EFDF] rounded-xl px-4 py-3 flex gap-3">
        <CheckI size={16} color="#1F5A41" />
        <p className="text-xs text-[#1F5A41] leading-relaxed font-medium">{t('bestResults')}</p>
      </div>

      <div className="space-y-3">
        <button onClick={() => fileInputRef.current?.click()} className={primaryBtn} style={display}>
          <UploadI size={20} color="#fff" />
          {t('upload')}
        </button>
        <button onClick={() => setCameraOpen(true)} className={secondaryBtn} style={display}>
          <CameraI size={20} color="#2D6A4F" />
          {t('takePhoto')}
        </button>
      </div>
      {fileInput}
    </div>
  )
}

// ── Loading ──────────────────────────────────────────────────────────────────

export function LoadingContent({ image }: { image: string | null }) {
  const { t } = useT()
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const id = setTimeout(() => setSlow(true), 6000)
    return () => clearTimeout(id)
  }, [])
  return (
    <div className="flex flex-col items-center justify-center py-10 text-center" role="status" aria-live="polite">
      <div className="relative w-[min(300px,72vw)] aspect-square rounded-2xl overflow-hidden bg-[#1A201A] mb-7">
        {image ? (
          <img src={image} alt={t('submittedPhoto')} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <LeafI size={40} color="#52B788" />
          </div>
        )}
        <div className="scan-sweep" aria-hidden="true" />
        <div className="scan-line" aria-hidden="true" />
      </div>
      <h2 className="text-xl font-bold text-[#1A201A]" style={display}>
        {t('analysing')}
      </h2>
      <p className={`text-sm mt-3 transition-opacity duration-300 ${slow ? 'opacity-100' : 'opacity-0'}`} style={{ color: MUTED }}>
        {t('analysingSlow')}
      </p>
    </div>
  )
}

// ── Results ──────────────────────────────────────────────────────────────────

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

function ConfidenceRing({ value, tone, label }: { value: number; tone: Tone; label: string }) {
  const { t } = useT()
  const R = 44
  const C = 2 * Math.PI * R
  const [on, setOn] = useState(false)
  useEffect(() => {
    const id = setTimeout(() => setOn(true), 120)
    return () => clearTimeout(id)
  }, [])
  const v = Math.min(100, Math.max(0, value))
  return (
    <div className="relative w-[104px] h-[104px] flex-shrink-0" role="img" aria-label={`${t('confidence')} ${label}`}>
      <svg viewBox="0 0 104 104" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="52" cy="52" r={R} fill="none" stroke="#E8E4DB" strokeWidth="9" />
        <circle
          cx="52"
          cy="52"
          r={R}
          fill="none"
          stroke={TONES[tone].bar}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={on ? C * (1 - v / 100) : C}
          style={{ transition: 'stroke-dashoffset 900ms cubic-bezier(.2,.8,.2,1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
        <span className="text-2xl font-extrabold text-[#1A201A] leading-none" style={display}>
          {label}
        </span>
        <span className="text-[11px] mt-1" style={{ color: MUTED }}>
          {t('confidence')}
        </span>
      </div>
    </div>
  )
}

function TopBars({ result, tone }: { result: AnalyseResult; tone: Tone }) {
  const { t } = useT()
  const items = result.top.slice(0, 3)
  return (
    <section className="bg-white border border-[#DDD8CE] rounded-2xl p-4">
      <h3 className="text-sm font-bold text-[#1A201A] mb-3" style={display}>
        {t('top3')}
      </h3>
      <ol className="space-y-3">
        {items.map((g, i) => (
          <li key={g.label + i}>
            <div className="flex items-baseline justify-between gap-3 text-sm mb-1">
              <span className={i === 0 ? 'font-bold text-[#1A201A]' : 'text-[#3A4A38]'}>{g.name}</span>
              <span className="font-bold tabular-nums" style={{ ...display, color: i === 0 ? TONES[tone].fg : '#3A4A38' }}>
                {fmtPct(g.prob)}
              </span>
            </div>
            <div className="h-2.5 bg-[#E8E4DB] rounded-full overflow-hidden" role="meter" aria-label={g.name} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct(g.prob))}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, pct(g.prob))}%`,
                  backgroundColor: i === 0 ? TONES[tone].bar : '#6F8A77',
                  transition: 'width 600ms ease-out',
                }}
              />
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

function CompareSlider({ photo, heatmap }: { photo: string; heatmap: string }) {
  const { t } = useT()
  const [pos, setPos] = useState(50)
  return (
    <figure className="bg-white border border-[#DDD8CE] rounded-2xl p-3">
      <div className="relative aspect-square rounded-xl overflow-hidden bg-[#1A201A] select-none">
        <img src={photo} alt={t('photoAlt')} className="absolute inset-0 w-full h-full object-cover" draggable={false} />
        <img src={heatmap} alt={t('heatmapAlt')} className="absolute inset-0 w-full h-full object-cover" style={{ clipPath: `inset(0 0 0 ${pos}%)` }} draggable={false} />
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={pos}
          onChange={(e) => setPos(Number(e.target.value))}
          aria-label={t('compareHint')}
          aria-valuetext={`${t('photo')} ${pos}% / ${t('heatmap')} ${100 - pos}%`}
          className="peer absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-10"
          style={{ touchAction: 'pan-y', minHeight: 44 }}
        />
        <div className="absolute inset-y-0 w-0.5 bg-white pointer-events-none shadow-[0_0_6px_rgba(0,0,0,0.5)]" style={{ left: `${pos}%` }} aria-hidden="true">
          <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white shadow-lg flex items-center justify-center text-[#2D6A4F] font-bold text-lg">
            ⇆
          </span>
        </div>
        <span className="absolute top-2 left-2 text-xs font-bold text-white bg-black/65 rounded-full px-2.5 py-1 pointer-events-none">{t('photo')}</span>
        <span className="absolute top-2 right-2 text-xs font-bold text-white bg-black/65 rounded-full px-2.5 py-1 pointer-events-none">{t('heatmap')}</span>
        <span className="absolute inset-0 rounded-xl ring-4 ring-[#52B788] ring-inset opacity-0 peer-focus-visible:opacity-100 pointer-events-none" aria-hidden="true" />
      </div>
      <figcaption className="flex items-center gap-2 text-sm mt-3 px-1" style={{ color: '#3A4A38' }}>
        <span className="w-3 h-3 rounded-full bg-[#E41212] flex-shrink-0" aria-hidden="true" />
        {t('compareCaption')}
      </figcaption>
    </figure>
  )
}

function About({ info }: { info: AnalyseResult['model_info'] }) {
  const { t } = useT()
  const rows: [string, number | undefined][] = [
    [t('cleanAcc'), info.clean_accuracy],
    [t('fieldAcc'), info.field_accuracy],
  ]
  return (
    <details className="group bg-white border border-[#DDD8CE] rounded-2xl">
      <summary className="flex items-center justify-between gap-3 min-h-12 px-4 py-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden rounded-2xl">
        <span className="text-sm font-bold text-[#1A201A]" style={display}>
          {t('about')}
        </span>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2D6A4F" strokeWidth="2.5" strokeLinecap="round" className="transition-transform duration-200 group-open:rotate-180" aria-hidden="true">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </summary>
      <div className="px-4 pb-4 space-y-2 text-sm text-[#3A4A38] leading-relaxed">
        <p>{info.note}</p>
        {rows.map(([label, v]) =>
          v == null ? null : (
            <p key={label} className="flex justify-between gap-3 border-t border-[#EEE9DF] pt-2">
              <span>{label}</span>
              <span className="font-bold text-[#1A201A]">{fmtPct(v)}</span>
            </p>
          )
        )}
      </div>
    </details>
  )
}

function Badge({ tone, children }: { tone: 'good' | 'bad'; children: ReactNode }) {
  const c = TONES[tone]
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold" style={{ backgroundColor: c.bg, color: c.fg, ...display }}>
      {tone === 'good' ? <CheckI size={15} /> : <AlertI size={15} />}
      {children}
    </span>
  )
}

export function ResultsContent({
  task,
  result,
  onRetry,
  onLearn,
}: {
  task: Task
  result: AnalyseResult
  onRetry: () => void
  onLearn?: (cropId: string, diseaseId: string, label: string) => void
}) {
  const { t } = useT()
  const best = result.top[0]
  const isProduce = task === 'produce'

  const rotten = result.state ? result.state.name === 'rotten' : /rotten/i.test(best?.name ?? '')
  const healthy = isProduce ? !rotten : isHealthyName(`${best?.label ?? ''} ${best?.name ?? ''}`)
  const tone: Tone = !result.confident ? 'unsure' : isProduce ? (rotten ? 'bad' : 'good') : healthy ? 'good' : 'warn'

  const fruitName = result.fruit?.name
  const stateWord = result.state ? t(result.state.name) : null
  const headline = !result.confident
    ? t('notSure')
    : isProduce && fruitName && stateWord
      ? `${stateWord} ${fruitName.toLowerCase()}`
      : (best?.name ?? '')

  const ringValue = best ? pct(best.prob) : result.state ? pct(result.state.prob) : null
  const ringLabel = ringValue == null ? '' : `${Math.round(ringValue)}%`

  const statusText = !result.confident ? null : isProduce ? (rotten ? t('rotten') : t('fresh')) : healthy ? t('healthy') : t('disease')
  const hasTreatment = (task === 'leaf' || task === 'pest') && result.confident && !!(result.advice || result.source || result.disclaimer)

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2 lg:gap-6 lg:items-start">
        <div className="space-y-4 lg:order-2 animate-fade-up">
          {!result.confident && (
            <div role="alert" className="rounded-2xl border border-[#F0C27A] bg-[#FFF4DC] p-4 space-y-3">
              <div className="flex gap-3">
                <AlertI size={22} color="#8A4B00" />
                <p className="text-base font-bold text-[#6B3A00] leading-snug" style={display}>
                  {t('lowConf')}
                </p>
              </div>
              <button onClick={onRetry} className={primaryBtn} style={display}>
                <CameraI size={20} color="#fff" />
                {t('retake')}
              </button>
            </div>
          )}

          <section className="bg-white border border-[#DDD8CE] rounded-2xl p-4">
            <div className="flex items-center gap-4">
              {ringValue != null && <ConfidenceRing value={ringValue} tone={tone} label={ringLabel} />}
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wide mb-0.5" style={{ color: MUTED }}>
                  {t('result')}
                </p>
                <h2 className="text-2xl font-extrabold text-[#1A201A] leading-tight break-words" style={display}>
                  {headline}
                </h2>
                {statusText && (
                  <span className="inline-flex items-center gap-1.5 mt-2 rounded-full px-3 py-1 text-xs font-bold" style={{ backgroundColor: TONES[tone].bg, color: TONES[tone].fg, ...display }}>
                    {healthy ? <CheckI size={14} /> : <AlertI size={14} />}
                    {statusText}
                  </span>
                )}
                {!result.confident && best && (
                  <p className="text-sm mt-1" style={{ color: MUTED }}>
                    {t('closest')}: <span className="font-semibold text-[#3A4A38]">{best.name}</span>
                  </p>
                )}
              </div>
            </div>
            {isProduce && (result.fruit || result.state) && (
              <div className="flex flex-wrap gap-2 mt-4">
                {result.fruit && (
                  <Badge tone={rotten ? 'bad' : 'good'}>
                    {t('fruit')}: {result.fruit.name} {fmtPct(result.fruit.prob)}
                  </Badge>
                )}
                {result.state && (
                  <Badge tone={result.state.name === 'rotten' ? 'bad' : 'good'}>
                    {t('condition')}: {t(result.state.name)} {fmtPct(result.state.prob)}
                  </Badge>
                )}
              </div>
            )}
          </section>

          <TopBars result={result} tone={tone} />
        </div>

        <div className="space-y-4 lg:order-1 animate-fade-up" style={{ animationDelay: '120ms' }}>
          <CompareSlider photo={result.images.photo} heatmap={result.images.heatmap} />

          {hasTreatment && (
            <section className="bg-[#EEF5EF] border border-[#CFE3D5] rounded-2xl p-4 space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-[#2D6A4F] flex items-center justify-center flex-shrink-0">
                  <LeafI size={16} color="#fff" />
                </span>
                <h3 className="text-sm font-bold text-[#1A201A]" style={display}>
                  {t('treatment')}
                </h3>
              </div>
              {result.advice && <p className="text-sm text-[#2E3F2E] leading-relaxed">{result.advice}</p>}
              {result.source && (
                <p className="text-xs" style={{ color: MUTED }}>
                  {t('source')}: {result.source}
                </p>
              )}
              {result.disclaimer && <p className="text-xs italic border-t border-[#CFE3D5] pt-2" style={{ color: MUTED }}>{result.disclaimer}</p>}
            </section>
          )}

          <About info={result.model_info} />
        </div>
      </div>

      {result.confident && best && (
        <ScanFollowUp
          task={task}
          label={isProduce ? headline : best.name}
          confidence={pct(best.prob)}
          isHealthy={healthy}
          onLearn={onLearn}
        />
      )}

      {result.confident && (
        <button onClick={onRetry} className={primaryBtn} style={display}>
          <RetryI size={18} color="#fff" />
          {t('tryAnother')}
        </button>
      )}

      <p className="flex items-start gap-2 text-xs leading-relaxed" style={{ color: MUTED }}>
        <AlertI size={14} />
        {t('mistakes')}
      </p>
    </div>
  )
}

// ── Error / empty ────────────────────────────────────────────────────────────

export function ErrorContent({ error, canRetrySame, onRetrySame, onReset }: { error: AnalyseError | null; canRetrySame: boolean; onRetrySame: () => void; onReset: () => void }) {
  const { t } = useT()
  const kind = error?.kind ?? 'server'
  const copy = {
    unreadable: [t('errUnreadable'), t('errUnreadableBody')],
    tooLarge: [t('errTooLarge'), t('errTooLargeBody')],
    empty: [t('errEmpty'), t('errEmptyBody')],
    network: [t('errNetwork'), t('errNetworkBody')],
    server: [t('errServer'), t('errServerBody')],
  }[kind]
  const transient = (kind === 'network' || kind === 'server') && canRetrySame
  const soft = kind === 'empty'
  return (
    <div role="alert" className="flex flex-col items-center justify-center py-16 text-center animate-fade-up">
      <div className={`w-20 h-20 rounded-full flex items-center justify-center mb-6 animate-shake ${soft ? 'bg-[#E8E4DB]' : 'bg-[#FCE4E4]'}`}>
        {soft ? <CameraI size={34} color="#3A4A38" /> : <AlertI size={34} color="#A81F1F" />}
      </div>
      <h2 className="text-xl font-extrabold text-[#1A201A] mb-2" style={display}>
        {copy[0]}
      </h2>
      <p className="text-sm leading-relaxed mb-8 max-w-xs" style={{ color: MUTED }}>
        {copy[1]}
      </p>
      <div className="w-full max-w-xs space-y-3">
        {transient ? (
          <>
            <button onClick={onRetrySame} className={primaryBtn} style={display}>
              <RetryI size={18} color="#fff" />
              {t('tryAgain')}
            </button>
            <button onClick={onReset} className={secondaryBtn} style={display}>
              {t('chooseAnother')}
            </button>
          </>
        ) : (
          <button onClick={onReset} className={primaryBtn} style={display}>
            <RetryI size={18} color="#fff" />
            {t('chooseAnother')}
          </button>
        )}
      </div>
    </div>
  )
}
