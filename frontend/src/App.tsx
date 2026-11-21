import { useState, useRef, useEffect } from 'react'
import FarmTools, { type ToolFocus } from './hub/FarmTools'
import Overview from './hub/Overview'
import ScanFollowUp from './hub/ScanFollowUp'
import { TOOLS, ToolIcon, type ToolId } from './hub/ui'
import { AnalyseError, analyse, type AnalyseResult, type Task } from './lib/api'
import { LangProvider, useT } from './lib/i18n'
import { ErrorContent, InputMethodContent, LoadingContent, ResultsContent } from './scan/ScanViews'

// ── Types & mock data ─────────────────────────────────────────────────────────

type PanelState = 'input' | 'loading' | 'results' | 'error'
type MobileScreen = 'landing' | 'task-picker' | 'working' | 'tool'

// ── Media query hook ──────────────────────────────────────────────────────────

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== 'undefined' && window.innerWidth >= 768
  )
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    setIsDesktop(mq.matches)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])
  return isDesktop
}

// ── SVG icons ─────────────────────────────────────────────────────────────────

function LeafIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2C6.5 2 3 6 3 12c0 4.5 3 8 9 9 1-3 1-6 0-8.5C9.5 10 7 10 7 10s1-4 5-4c3.5 0 7 2 7 8 0 3.5-2 6-4 7h-1c6-1 8-5 8-9 0-6-4-10-10-10z"
        fill={color}
      />
    </svg>
  )
}

function BugIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="14" rx="4" ry="5.5" fill={color} fillOpacity={0.2} />
      <path d="M9 8.5c0-1.7 1.3-3 3-3s3 1.3 3 3M10 5L8.5 3M14 5l1.5-2M8 12H4M16 12h4M8.5 16L5 18M15.5 16l3.5 2M12 9v10" />
    </svg>
  )
}
function AppleIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M17 8c-.5-1.5-2-3-4-3s-3.5 1.5-4 3c-1.5.5-3 2-3 5 0 4 2 7 5 7 .7 0 1.3-.3 2-.3s1.3.3 2 .3c3 0 5-3 5-7 0-3-1.5-4.5-3-5zm-2-4c.5-.7 1-1.5 1-2.5-.8.2-2 .8-2.5 2 .5-.1 1 .5 1.5.5z"
        fill={color}
      />
    </svg>
  )
}

function CameraIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2v11z"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="13" r="4" stroke={color} strokeWidth="1.8" />
    </svg>
  )
}

function UploadIcon({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ArrowRight({ size = 20, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M5 12h14M12 5l7 7-7 7" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function HomeIcon({ size = 20, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ChevronLeft({ size = 20, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M15 18l-6-6 6-6" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function AlertCircle({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.8" />
      <line x1="12" y1="8" x2="12" y2="12" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
      <line x1="12" y1="16" x2="12.01" y2="16" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function CheckCircle({ size = 24, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.8" />
      <path d="M8 12l3 3 5-5" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ScanIcon({ size = 16, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="3" stroke={color} strokeWidth="1.8" />
      <path
        d="M3 9V5a2 2 0 0 1 2-2h4M3 15v4a2 2 0 0 0 2 2h4M21 9V5a2 2 0 0 0-2-2h-4M21 15v4a2 2 0 0 1-2 2h-4"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}

// ── Botanical decoration ──────────────────────────────────────────────────────

const LEAF = 'M0 0C8 -11 22 -11 32 0C22 11 8 11 0 0Z'

function LeafSprig({
  className = '',
  color = '#52B788',
  opacity = 1,
}: {
  className?: string
  color?: string
  opacity?: number
}) {
  const leaves: [number, number, number, number][] = [
    [40, 150, -60, 0.9],
    [52, 128, 50, 0.9],
    [64, 104, -55, 1],
    [74, 82, 48, 1],
    [84, 60, -50, 0.9],
    [92, 40, 45, 0.8],
    [100, 20, -70, 0.7],
  ]
  return (
    <svg
      aria-hidden
      viewBox="0 0 140 180"
      fill="none"
      className={`pointer-events-none select-none ${className}`}
      style={{ opacity }}
    >
      <path d="M30 178C34 130 70 80 108 8" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
      {leaves.map(([x, y, rot, sc], i) => (
        <path key={i} d={LEAF} fill={color} transform={`translate(${x} ${y}) rotate(${rot}) scale(${sc})`} />
      ))}
      <path d={LEAF} fill={color} transform="translate(108 8) rotate(-95) scale(0.9)" />
    </svg>
  )
}

function Eyebrow({ children, light = false }: { children: React.ReactNode; light?: boolean }) {
  return (
    <p
      className={`flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] mb-3 ${
        light ? 'text-[#95D5B2]' : 'text-[#2D6A4F]'
      }`}
    >
      <LeafIcon size={13} color={light ? '#95D5B2' : '#52B788'} />
      {children}
    </p>
  )
}

// ── Shared UI components ──────────────────────────────────────────────────────

// ── Panel state manager (shared logic for both layouts) ────────────────────────

function usePanelManager(task: Task) {
  const [panelState, setPanelState] = useState<PanelState>('input')
  const [result, setResult] = useState<AnalyseResult | null>(null)
  const [error, setError] = useState<AnalyseError | null>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const taskRef = useRef(task)
  taskRef.current = task
  const fileRef = useRef<File | null>(null)
  const runId = useRef(0)

  function clearPreview() {
    setUploadedImage((prev) => {
      if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev)
      return null
    })
  }

  async function run(file: File) {
    const id = ++runId.current
    setError(null)
    setPanelState('loading')
    try {
      const res = await analyse(taskRef.current, file)
      if (id !== runId.current) return
      setResult(res)
      setPanelState('results')
    } catch (e) {
      if (id !== runId.current) return
      setError(e instanceof AnalyseError ? e : new AnalyseError('server'))
      setPanelState('error')
    }
  }

  function handleCapture(file: File) {
    fileRef.current = file
    clearPreview()
    setUploadedImage(file.size > 0 ? URL.createObjectURL(file) : null)
    void run(file)
  }

  function handleRetrySame() {
    if (fileRef.current) void run(fileRef.current)
  }

  function handleRetry() {
    runId.current++
    fileRef.current = null
    clearPreview()
    setResult(null)
    setError(null)
    setPanelState('input')
  }

  return { panelState, result, error, uploadedImage, handleCapture, handleRetry, handleRetrySame, hasFile: !!fileRef.current }
}

// ── Desktop layout ─────────────────────────────────────────────────────────────

const TASK_META: Record<Task, { label: string; subtitle: string }> = {
  leaf: { label: 'Diagnose Leaf', subtitle: '12 crops' },
  produce: { label: 'Grade Produce', subtitle: '14 crops' },
  pest: { label: 'Identify Pest', subtitle: 'Tomato only' },
}

function useTaskMeta() {
  const { t } = useT()
  return {
    leaf: { label: t('diagnoseLeaf'), subtitle: TASK_META.leaf.subtitle },
    produce: { label: t('gradeProduce'), subtitle: TASK_META.produce.subtitle },
    pest: { label: t('identifyPest'), subtitle: TASK_META.pest.subtitle },
  } as Record<Task, { label: string; subtitle: string }>
}

function DesktopSidebar({
  activeTask,
  onTaskSelect,
  onHome,
  panelState,
  tool,
  onTool,
}: {
  activeTask: Task
  onTaskSelect: (t: Task) => void
  onHome: () => void
  panelState: PanelState
  tool: ToolId | null
  onTool: (t: ToolId) => void
}) {
  const taskMeta = useTaskMeta()
  const { t } = useT()
  const toolLabels: Record<ToolId, string> = {
    overview: t('farmOverview'),
    hub: t('knowledgeHub'),
    care: t('cropCareGuide'),
    calendar: t('cropCalendar'),
    journal: t('farmJournal'),
  }
  return (
    <div className="w-[4.5rem] lg:w-56 flex-none flex flex-col bg-[#2D6A4F] text-white h-dvh sticky top-0 overflow-hidden">
      {/* Brand */}
      <button
        onClick={onHome}
        aria-label="FarmSight home"
        className="text-left px-3 lg:px-5 pt-8 pb-5 border-b border-white/10 hover:bg-white/5 transition-colors duration-150"
      >
        <div className="flex items-center justify-center lg:justify-start gap-2.5 mb-1">
          <div className="w-7 h-7 bg-[#52B788] rounded-full flex items-center justify-center flex-shrink-0">
            <LeafIcon size={14} color="white" />
          </div>
          <span className="hidden lg:inline font-bold text-base" style={{ fontFamily: 'Manrope, sans-serif' }}>
            FarmSight
          </span>
        </div>
        <p className="hidden lg:block text-white/80 text-xs pl-[36px]">AI-powered field analysis</p>
      </button>

      {/* Nav */}
      <nav className="flex-1 px-2 lg:px-3 py-5 space-y-1 overflow-y-auto">
        <button
          onClick={onHome}
          className="w-full text-left px-2 lg:px-3 py-2.5 rounded-xl flex items-center justify-center lg:justify-start gap-3 hover:bg-white/10 transition-colors duration-150 mb-4"
        >
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0">
            <HomeIcon size={16} color="white" />
          </div>
          <span className="hidden lg:inline text-sm font-semibold" style={{ fontFamily: 'Manrope, sans-serif' }}>
            {t('home')}
          </span>
        </button>
        <p className="hidden lg:block text-white/80 text-[10px] font-bold uppercase tracking-wider px-2 mb-3">
          {t('tasks')}
        </p>
        {(['leaf', 'produce', 'pest'] as Task[]).map((t) => {
          const meta = taskMeta[t]
          const isActive = !tool && activeTask === t
          return (
            <button
              key={t}
              onClick={() => onTaskSelect(t)}
              title={meta.label}
              aria-label={meta.label}
              className={`w-full text-left px-2 lg:px-3 py-3 rounded-xl flex items-center justify-center lg:justify-start gap-3 transition-colors duration-150 ${
                isActive ? 'bg-white' : 'hover:bg-white/10'
              }`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors duration-150 ${
                  isActive ? 'bg-[#D8EFDF]' : 'bg-white/10'
                }`}
              >
                {t === 'leaf' ? (
                  <LeafIcon size={16} color={isActive ? '#2D6A4F' : 'white'} />
                ) : t === 'pest' ? (
                  <BugIcon size={16} color={isActive ? '#8A4A1C' : 'white'} />
                ) : (
                  <AppleIcon size={16} color={isActive ? '#E07B39' : 'white'} />
                )}
              </div>
              <div className="min-w-0 hidden lg:block">
                <p
                  className={`text-sm font-semibold truncate ${isActive ? 'text-[#2D6A4F]' : 'text-white'}`}
                  style={{ fontFamily: 'Manrope, sans-serif' }}
                >
                  {meta.label}
                </p>
                <p className={`text-xs truncate ${isActive ? 'text-[#5A6A59]' : 'text-white/80'}`}>
                  {meta.subtitle}
                </p>
              </div>
            </button>
          )
        })}
        <p className="hidden lg:block text-white/80 text-[10px] font-bold uppercase tracking-wider px-2 pt-4 mb-3">
          {t('knowledgeFarm')}
        </p>
        <div className="lg:hidden border-t border-white/10 my-3" />
        {TOOLS.map((t) => {
          const on = tool === t.id
          return (
            <button
              key={t.id}
              onClick={() => onTool(t.id)}
              title={toolLabels[t.id]}
              aria-label={toolLabels[t.id]}
              aria-current={on ? 'page' : undefined}
              className={`w-full text-left px-2 lg:px-3 py-2.5 rounded-xl flex items-center justify-center lg:justify-start gap-3 transition-colors duration-150 ${
                on ? 'bg-white' : 'hover:bg-white/10'
              }`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${on ? 'bg-[#D8EFDF]' : 'bg-white/10'}`}>
                <ToolIcon id={t.id} color={on ? '#2D6A4F' : 'white'} />
              </div>
              <div className="min-w-0 hidden lg:block">
                <p className={`text-sm font-semibold truncate ${on ? 'text-[#2D6A4F]' : 'text-white'}`} style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {toolLabels[t.id]}
                </p>
                <p className={`text-xs truncate ${on ? 'text-[#5A6A59]' : 'text-white/80'}`}>{t.subtitle}</p>
              </div>
            </button>
          )
        })}
      </nav>

      {/* Status indicator */}
      <div className="px-3 lg:px-5 py-4 border-t border-white/10">
        <div className="flex items-center justify-center lg:justify-start gap-2">
          <div
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              panelState === 'loading' ? 'bg-[#52B788] animate-pulse-dot' : 'bg-[#52B788]'
            }`}
          />
          <p className="hidden lg:block text-white/80 text-xs">
            {panelState === 'loading' ? t('processing') : t('modelReady')}
          </p>
        </div>
      </div>
    </div>
  )
}

function DesktopApp({ onHome }: { onHome: () => void }) {
  const [activeTask, setActiveTask] = useState<Task>('leaf')
  const [tool, setTool] = useState<ToolId | null>(null)
  const [focus, setFocus] = useState<ToolFocus>({})
  const panel = usePanelManager(activeTask)
  const taskMeta = useTaskMeta()
  const { t: tr } = useT()
  const toolLabels: Record<ToolId, string> = {
    overview: tr('farmOverview'),
    hub: tr('knowledgeHub'),
    care: tr('cropCareGuide'),
    calendar: tr('cropCalendar'),
    journal: tr('farmJournal'),
  }
  const toolSubtitles: Record<ToolId, string> = {
    overview: tr('tasksAndShortcuts'),
    hub: tr('cropProfilesSearch'),
    care: tr('soilNutrientsPrevention'),
    calendar: tr('stagesAndTasks'),
    journal: tr('recordsAndScans'),
  }

  function openTool(t: ToolId, cropId?: string) {
    setFocus({ cropId })
    setTool(t)
  }

  function openScan(t: Task) {
    setTool(null)
    if (t !== activeTask) {
      setActiveTask(t)
      panel.handleRetry()
    }
  }

  function handleLearn(cropId: string, diseaseId: string, label: string) {
    setFocus({ cropId, diseaseId, scanLabel: label })
    setTool('care')
  }

  function handleTaskSwitch(t: Task) {
    if (tool) {
      setTool(null)
      if (t === activeTask) return
    }
    if (t === activeTask) return
    setActiveTask(t)
    panel.handleRetry()
  }

  return (
    <div className="relative flex h-dvh bg-gradient-to-br from-[#E3F1E7] via-[#F5F2EC] to-[#F5F2EC] overflow-hidden">
      <DesktopSidebar
        activeTask={activeTask}
        onTaskSelect={handleTaskSwitch}
        onHome={onHome}
        panelState={panel.panelState}
        tool={tool}
        onTool={(t) => openTool(t)}
      />

      {/* Working panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Panel header */}
        <div className="flex-none flex items-center justify-between gap-3 px-[clamp(1rem,3vw,2rem)] pt-[clamp(1.25rem,3vw,2rem)] pb-4 border-b border-[#DDD8CE] bg-[#F5F2EC]/70 backdrop-blur-sm">
          <div>
            <h1
              className="text-xl font-extrabold text-[#1A201A]"
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              {tool ? toolLabels[tool] : taskMeta[activeTask].label}
            </h1>
            <p className="text-xs text-[#5A6A59] mt-0.5">
              {tool ? toolSubtitles[tool] : taskMeta[activeTask].subtitle}
            </p>
          </div>
          <div className="flex items-center gap-3">
          {!tool && panel.panelState !== 'input' && panel.panelState !== 'loading' && (
            <button
              onClick={panel.handleRetry}
              className="flex items-center gap-2 text-sm font-semibold text-[#1F5A41] bg-[#D8EFDF] hover:bg-[#C3E5CC] min-h-11 px-4 py-2 rounded-xl transition-colors"
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path
                  d="M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15"
                  stroke="#2D6A4F"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {tr('newAnalysis')}
            </button>
          )}
          </div>
        </div>

        {/* Scrollable content area */}
        <LeafSprig className="absolute bottom-0 right-0 w-40 xl:w-56 translate-x-6 translate-y-6 rotate-[-12deg]" color="#52B788" opacity={0.25} />
        <div className="flex-1 overflow-y-auto px-[clamp(1rem,3vw,2rem)] py-[clamp(1.25rem,2.5vw,1.75rem)]">
          {tool && (
            <div className="w-full max-w-3xl mx-auto animate-fade-in">
              <FarmTools tool={tool} focus={focus} onTool={openTool} onScan={openScan} />
            </div>
          )}
          <div key={`${activeTask}-${panel.panelState}`} className={`w-full mx-auto animate-fade-in ${panel.panelState === 'results' ? 'max-w-4xl' : 'max-w-lg xl:max-w-xl'} ${tool ? 'hidden' : ''}`}>
            {panel.panelState === 'input' && (
              <InputMethodContent task={activeTask} onCapture={panel.handleCapture} />
            )}
            {panel.panelState === 'loading' && <LoadingContent image={panel.uploadedImage} />}
            {panel.panelState === 'results' && panel.result && (
              <ResultsContent
                task={activeTask}
                result={panel.result}
                onRetry={panel.handleRetry}
                onLearn={handleLearn}
              />
            )}
            {panel.panelState === 'error' && (
              <ErrorContent error={panel.error} canRetrySame={panel.hasFile} onRetrySame={panel.handleRetrySame} onReset={panel.handleRetry} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Mobile layout ──────────────────────────────────────────────────────────────

function TopBar({
  onBack,
  onHome,
  title,
  light = false,
}: {
  onBack?: () => void
  onHome?: () => void
  title?: string
  light?: boolean
}) {
  const { t } = useT()
  return (
    <div className={`flex items-center gap-3 px-[clamp(1rem,5vw,1.25rem)] pt-12 pb-4 ${light ? 'text-white' : 'text-[#1A201A]'}`}>
      {onBack && (
        <button
          onClick={onBack}
          className={`flex items-center justify-center w-11 h-11 rounded-full transition-colors ${
            light ? 'bg-white/15 hover:bg-white/25' : 'bg-[#E8E4DB] hover:bg-[#DDD8CE]'
          }`}
          aria-label="Go back"
        >
          <ChevronLeft size={18} color={light ? 'white' : '#1A201A'} />
        </button>
      )}
      {title && (
        <span
          className="text-sm font-semibold tracking-wide uppercase opacity-70"
          style={{ fontFamily: 'Manrope, sans-serif' }}
        >
          {title}
        </span>
      )}
      <div className="ml-auto flex items-center gap-2">
      {onHome && (
        <button
          onClick={onHome}
          className={`flex items-center justify-center w-11 h-11 rounded-full transition-colors ${
            light ? 'bg-white/15 hover:bg-white/25' : 'bg-[#E8E4DB] hover:bg-[#DDD8CE]'
          }`}
          aria-label={t('home')}
        >
          <HomeIcon size={18} color={light ? 'white' : '#1A201A'} />
        </button>
      )}
      </div>
    </div>
  )
}

const CROPS = [
  {
    name: 'Tomato',
    note: 'Leaf disease',
    image: 'https://images.unsplash.com/photo-1582284540020-8acbe03f4924?w=700&h=700&fit=crop&auto=format',
  },
  {
    name: 'Potato',
    note: 'Leaf disease',
    image: 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=700&h=700&fit=crop&auto=format',
  },
  {
    name: 'Apple',
    note: 'Fresh or rotten',
    image: 'https://images.unsplash.com/photo-1628486930972-c1db82d528da?w=700&h=700&fit=crop&auto=format',
  },
  {
    name: 'Orange',
    note: 'Fresh or rotten',
    image: 'https://images.unsplash.com/photo-1638450060428-112a559ac3c7?w=700&h=700&fit=crop&auto=format',
  },
]

function LandingHero({ onStart }: { onStart: () => void }) {
  const { t } = useT()
  return (
    <div className="min-h-[85dvh] w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] pt-[clamp(1.5rem,6vw,4rem)] pb-8 flex flex-col md:flex-row md:items-center md:gap-[clamp(2rem,5vw,3.5rem)]">
      <div className="md:flex-1 animate-fade-up">
        <div className="flex items-center justify-between gap-2.5 mb-6 md:mb-8">
          <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-[#2D6A4F] flex items-center justify-center">
            <LeafIcon size={18} color="white" />
          </div>
          <span
            className="text-xl font-bold tracking-tight text-[#1A201A]"
            style={{ fontFamily: 'Manrope, sans-serif' }}
          >
            FarmSight
          </span>
          </div>
        </div>
        <h1
          className="text-[clamp(1.875rem,7vw,3.25rem)] font-extrabold leading-[1.08] tracking-tight text-[#1A201A] mb-4"
          style={{ fontFamily: 'Manrope, sans-serif' }}
        >
          Know your crop
          <br />
          <span className="text-[#2D6A4F]">before it shows.</span>
        </h1>
        <p className="text-[#3A4A38] text-base leading-relaxed mb-6 md:max-w-md">
          Photograph a leaf from 12 crops to spot disease, grade 14 kinds of produce, or identify
          tomato pests — with a heatmap showing exactly what the AI saw.
        </p>

        <div className="flex flex-wrap gap-2 mb-8">
          {['Heatmap explanations', 'Treatment tips', 'No account needed'].map((t) => (
            <span
              key={t}
              className="flex items-center gap-1.5 text-xs font-medium text-[#2D6A4F] bg-[#D8EFDF] px-3 py-1.5 rounded-full"
            >
              <ScanIcon size={12} color="#2D6A4F" />
              {t}
            </span>
          ))}
        </div>

        <button
          onClick={onStart}
          className="hidden md:flex items-center justify-center gap-3 bg-[#2D6A4F] text-white font-bold text-base px-8 py-4 rounded-2xl hover:bg-[#235a41] tap"
          style={{ fontFamily: 'Manrope, sans-serif' }}
        >
          {t('getStarted')}
          <ArrowRight size={18} color="white" />
        </button>
      </div>

      <div className="md:flex-1 grid grid-cols-2 gap-3 md:gap-4 mb-8 md:mb-0">
        {CROPS.map((c, i) => (
          <div
            key={c.name}
            className={`relative rounded-3xl overflow-hidden aspect-[4/5] bg-[#E8E4DB] animate-fade-up ${
              i % 2 === 1 ? 'translate-y-4' : ''
            }`}
            style={{ animationDelay: `${100 + i * 70}ms` }}
          >
            <img src={c.image} alt={c.name} className="absolute inset-0 w-full h-full object-cover" />
            <div
              className="absolute inset-0"
              style={{ background: 'linear-gradient(to top, rgba(20,40,28,0.78) 0%, rgba(20,40,28,0) 55%)' }}
            />
            <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
              <p className="text-lg font-extrabold leading-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {c.name}
              </p>
              <p className="text-xs text-white/75">{c.note}</p>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onStart}
        className="md:hidden mt-auto w-full flex items-center justify-center gap-3 bg-[#2D6A4F] text-white font-bold text-base py-4 rounded-2xl hover:bg-[#235a41] tap"
        style={{ fontFamily: 'Manrope, sans-serif' }}
      >
        {t('getStarted')}
        <ArrowRight size={18} color="white" />
      </button>
    </div>
  )
}

const PRODUCE_CROPS = ['Apple', 'Banana', 'Bell pepper', 'Carrot', 'Cucumber', 'Grape', 'Guava', 'Jujube', 'Mango', 'Orange', 'Pomegranate', 'Potato', 'Strawberry', 'Tomato']
const PEST_CROPS = ['Tomato']
const LEAF_CROPS = ['Apple', 'Bell pepper', 'Cucumber', 'Grape', 'Groundnut', 'Jute', 'Maize', 'Mango', 'Onion', 'Potato', 'Tomato', 'Turmeric']

const STRIP = [
  { name: 'Tomato', image: CROPS[0].image },
  { name: 'Potato', image: CROPS[1].image },
  { name: 'Apple', image: CROPS[2].image },
  { name: 'Banana', image: 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=200&h=200&fit=crop&auto=format' },
  { name: 'Orange', image: CROPS[3].image },
]

const STEPS = [
  {
    icon: <CameraIcon size={22} color="#2D6A4F" />,
    title: 'Snap a photo',
    text: 'Take a clear picture of a leaf or a piece of fruit, or upload one from your phone.',
  },
  {
    icon: <ScanIcon size={22} color="#2D6A4F" />,
    title: 'AI takes a look',
    text: 'A model tuned for your crop checks for disease or freshness in a few seconds.',
  },
  {
    icon: <CheckCircle size={22} color="#2D6A4F" />,
    title: 'Get a clear answer',
    text: 'See the result, how confident it is, and simple treatment guidance when it applies.',
  },
]

function LandingScreen({ onStart }: { onStart: () => void }) {
  return (
    <div className="relative overflow-hidden bg-gradient-to-b from-[#DCEFE1] via-[#EDF3E8] to-[#F5F2EC]">
      <LeafSprig className="absolute top-6 -right-6 w-36 md:w-56 rotate-12" color="#52B788" opacity={0.35} />
      <LeafSprig className="absolute top-[34rem] -left-8 w-28 md:w-44 -scale-x-100" color="#2D6A4F" opacity={0.18} />
      <div
        aria-hidden
        className="absolute -top-32 -right-32 w-[28rem] h-[28rem] rounded-full bg-[#D8EFDF] opacity-70 blur-3xl pointer-events-none"
      />
      <div
        aria-hidden
        className="absolute top-[40rem] -left-40 w-[26rem] h-[26rem] rounded-full bg-[#FDE8D8] opacity-60 blur-3xl pointer-events-none"
      />

      <div className="relative">
        <LandingHero onStart={onStart} />

        {/* Crop strip */}
        <section className="w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-8">
          <div className="flex items-center gap-3 mb-4 text-[#2D6A4F]">
            <span className="h-px flex-1 bg-[#B7DCC4]" />
            <LeafIcon size={14} color="#52B788" />
            <span className="text-[11px] font-bold uppercase tracking-[0.14em]">Works with</span>
            <LeafIcon size={14} color="#52B788" />
            <span className="h-px flex-1 bg-[#B7DCC4]" />
          </div>
          <div className="flex flex-wrap justify-center gap-2.5">
            {STRIP.map((c) => (
              <div
                key={c.name}
                className="flex items-center gap-2 bg-white border border-[#DDD8CE] rounded-full pl-1 pr-4 py-1"
              >
                <img src={c.image} alt="" className="w-8 h-8 rounded-full object-cover" />
                <span className="text-sm font-semibold text-[#1A201A]" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {c.name}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Explainability demo */}
        <section className="w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-10 md:py-16 flex flex-col md:flex-row md:items-center gap-8 md:gap-14">
          <div className="md:flex-1 relative rounded-3xl overflow-hidden aspect-square bg-[#1A201A] shadow-[0_20px_50px_-20px_rgba(26,32,26,0.45)]">
            <img
              src="https://images.unsplash.com/photo-1642307321395-b72347cbe944?w=800&h=800&fit=crop&auto=format"
              alt="Tomato leaf with AI heatmap"
              className="w-full h-full object-cover opacity-80"
            />
            <div
              aria-hidden="true"
              className="absolute inset-0 mix-blend-screen"
              style={{
                background:
                  'radial-gradient(circle at 54% 38%, rgba(228,18,18,.7), rgba(242,188,18,.4) 14%, rgba(48,210,72,.2) 24%, transparent 32%), radial-gradient(circle at 30% 64%, rgba(235,80,10,.55), rgba(242,188,18,.3) 10%, transparent 22%)',
              }}
            />
            <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/50 backdrop-blur-sm text-white text-xs font-medium px-2.5 py-1 rounded-lg">
              <span className="w-1.5 h-1.5 rounded-full bg-[#E41212] animate-pulse-dot" />
              Example heatmap
            </div>
          </div>
          <div className="md:flex-1">
            <Eyebrow>Explainable by design</Eyebrow>
            <h2
              className="text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold leading-tight tracking-tight text-[#1A201A] mb-3"
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              See what the AI sees.
            </h2>
            <p className="text-[#3A4A38] leading-relaxed md:max-w-md">
              Every result comes with a heatmap. Warm colours mark the exact spots that shaped the
              decision, so you can check the answer against what is in front of you.
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="relative bg-[#2D6A4F] rounded-t-[2.5rem] md:rounded-t-[4rem] mt-6 overflow-hidden">
          <LeafSprig className="absolute -top-4 -left-6 w-32 md:w-48 -rotate-12 -scale-x-100" color="#52B788" opacity={0.22} />
          <LeafSprig className="absolute -bottom-6 -right-4 w-36 md:w-52 rotate-[160deg]" color="#52B788" opacity={0.22} />
          <div className="relative w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-14 md:py-20">
          <div className="md:flex md:flex-col md:items-center mb-8">
            <Eyebrow light>How it works</Eyebrow>
            <h2
              className="text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold tracking-tight text-white md:text-center"
              style={{ fontFamily: 'Manrope, sans-serif' }}
            >
              Three steps, no setup.
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {STEPS.map((st, i) => (
              <div key={st.title} className="bg-white border border-[#DDD8CE] rounded-3xl p-5 card-lift">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-11 h-11 rounded-2xl bg-[#D8EFDF] flex items-center justify-center">
                    {st.icon}
                  </div>
                  <span
                    className="text-3xl font-extrabold text-[#E8E4DB]"
                    style={{ fontFamily: 'Manrope, sans-serif' }}
                  >
                    0{i + 1}
                  </span>
                </div>
                <h3 className="font-bold text-[#1A201A] mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {st.title}
                </h3>
                <p className="text-sm text-[#5A6A59] leading-relaxed">{st.text}</p>
              </div>
            ))}
          </div>
          </div>
        </section>

        {/* CTA banner */}
        <section className="w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-12">
          <div className="relative rounded-3xl overflow-hidden">
            <img
              src="https://images.unsplash.com/photo-1524486361537-8ad15938e1a3?w=1400&h=700&fit=crop&auto=format"
              alt="Rows of tomato plants in a greenhouse"
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#143420]/90 via-[#143420]/70 to-[#143420]/30" />
            <div className="relative p-[clamp(1.5rem,5vw,3rem)] text-white md:max-w-lg">
              <h2
                className="text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold leading-tight tracking-tight mb-2"
                style={{ fontFamily: 'Manrope, sans-serif' }}
              >
                Catch problems early.
              </h2>
              <p className="text-white/80 leading-relaxed mb-5">
                Spot disease before it spreads and sort fruit before it spoils.
              </p>
              <button
                onClick={onStart}
                className="inline-flex items-center gap-3 bg-white text-[#2D6A4F] font-bold px-7 py-3.5 rounded-2xl hover:bg-[#F5F2EC] tap"
                style={{ fontFamily: 'Manrope, sans-serif' }}
              >
                Start analysing
                <ArrowRight size={18} color="#2D6A4F" />
              </button>
            </div>
          </div>
        </section>

        <footer className="w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] pt-4 pb-10 text-center">
          <div className="flex justify-center gap-2 mb-3 opacity-60">
            <LeafIcon size={12} color="#52B788" />
            <LeafIcon size={16} color="#2D6A4F" />
            <LeafIcon size={12} color="#52B788" />
          </div>
          <p className="text-xs text-[#5A6A59] leading-relaxed">
            FarmSight can make mistakes and can&apos;t be 100% sure about any result. Use it as a
            guide and confirm important decisions with an expert.
          </p>
        </footer>
      </div>
    </div>
  )
}

function TaskPickerScreen({
  onSelect,
  onTool,
  onBack,
  onHome,
}: {
  onSelect: (t: Task) => void
  onTool: (t: ToolId, cropId?: string) => void
  onBack: () => void
  onHome: () => void
}) {
  const [picked, setPicked] = useState<Task | null>(null)
  function handlePick(id: Task) {
    if (picked) return
    setPicked(id)
    setTimeout(() => onSelect(id), 240)
  }
  const { t } = useT()
  return (
    <div className="flex flex-col min-h-dvh animate-fade-up">
      <TopBar onBack={onBack} onHome={onHome} title={t('chooseTask')} />
      <div className="flex-1 px-5 pt-2 pb-10">
        <div className="mb-7">
          <h2
            className="text-2xl font-extrabold text-[#1A201A] mb-1"
            style={{ fontFamily: 'Manrope, sans-serif' }}
          >
            What are you
            <br />
            analysing today?
          </h2>
          <p className="text-sm text-[#5A6A59]">
            Each option runs a separate AI model tuned for that task.
          </p>
        </div>
        <div className="space-y-4">
          {([
            {
              id: 'leaf' as Task,
              label: 'Diagnose Leaf',
              desc: 'Detect diseases on the leaves of 12 crops, from early blight in tomato and potato to problems in maize, jute and groundnut. Tomato pests can also be identified.',
              chips: LEAF_CROPS,
              iconBg: '#D8EFDF',
              iconHover: '#B6DFC5',
              icon: <LeafIcon size={28} color="#2D6A4F" />,
            },
            {
              id: 'produce' as Task,
              label: 'Grade Produce',
              desc: 'Grade 14 kinds of fruit and vegetables as fresh or rotten to reduce waste and improve quality.',
              chips: PRODUCE_CROPS,
              iconBg: '#FDE8D8',
              iconHover: '#F8C9A8',
              icon: <AppleIcon size={28} color="#E07B39" />,
            },
            {
              id: 'pest' as Task,
              label: 'Identify Pest',
              desc: 'Identify common tomato pests such as whiteflies, aphids and mites from a close-up photo, with management tips.',
              chips: PEST_CROPS,
              iconBg: '#F1E3D3',
              iconHover: '#E6CFB4',
              icon: <BugIcon size={28} color="#8A4A1C" />,
            },
          ] as const).map(({ id, label, desc, chips, iconBg, iconHover, icon }) => (
            <button
              key={id}
              onClick={() => handlePick(id)}
              className={`w-full text-left bg-white border-2 border-[#DDD8CE] hover:border-[#52B788] rounded-2xl p-5 flex gap-4 items-start card-lift group ${picked === id ? 'animate-select-pulse' : ''}`}
            >
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 transition-colors"
                style={{ backgroundColor: iconBg }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = iconHover)}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = iconBg)}
              >
                {icon}
              </div>
              <div className="flex-1 pt-0.5">
                <h3
                  className="text-lg font-bold text-[#1A201A] mb-1"
                  style={{ fontFamily: 'Manrope, sans-serif' }}
                >
                  {label}
                </h3>
                <p className="text-sm text-[#5A6A59] leading-relaxed">{desc}</p>
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  {chips.map((c) => (
                    <span
                      key={c}
                      className="text-xs font-medium bg-[#F5F2EC] text-[#3A4A38] border border-[#DDD8CE] px-2 py-0.5 rounded-full"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>
              <div className="self-center opacity-30 group-hover:opacity-100 transition-opacity">
                <ArrowRight size={16} color="#2D6A4F" />
              </div>
            </button>
          ))}
        </div>
        <div className="mt-9">
          <h3 className="text-lg font-extrabold text-[#1A201A] mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Knowledge &amp; farm tools
          </h3>
          <p className="text-sm text-[#5A6A59] mb-4">Crop profiles, care guidance, task planning and your journal.</p>
          <Overview onTool={onTool} />
          <div className="grid grid-cols-2 gap-2 mt-3">
            {TOOLS.filter((t) => t.id !== 'overview' && t.id !== 'hub').map((t) => (
              <button
                key={t.id}
                onClick={() => onTool(t.id)}
                className="tap flex items-center gap-2 bg-white border border-[#DDD8CE] rounded-xl px-3 py-3 text-sm font-semibold text-[#1A201A]"
                style={{ fontFamily: 'Manrope, sans-serif' }}
              >
                <ToolIcon id={t.id} color="#2D6A4F" />
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function MobileApp() {
  const [mobileScreen, setMobileScreen] = useState<MobileScreen>('landing')
  const [task, setTask] = useState<Task>('leaf')
  const [tool, setTool] = useState<ToolId>('overview')
  const [focus, setFocus] = useState<ToolFocus>({})
  const panel = usePanelManager(task)
  const taskMeta = useTaskMeta()
  const { t: tr } = useT()

  function openTool(t: ToolId, cropId?: string) {
    setFocus({ cropId })
    setTool(t)
    setMobileScreen('tool')
  }

  function handleLearn(cropId: string, diseaseId: string, label: string) {
    setFocus({ cropId, diseaseId, scanLabel: label })
    setTool('care')
    setMobileScreen('tool')
  }

  function handleTaskSelect(t: Task) {
    setTask(t)
    setMobileScreen('working')
    panel.handleRetry()
  }

  function handleHome() {
    setMobileScreen('landing')
    panel.handleRetry()
  }

  function handleMobileBack() {
    if (mobileScreen === 'working') {
      setMobileScreen('task-picker')
      panel.handleRetry()
    } else if (mobileScreen === 'tool') {
      setMobileScreen('task-picker')
    } else if (mobileScreen === 'task-picker') {
      setMobileScreen('landing')
    }
  }

  return (
    <div className="relative min-h-dvh bg-gradient-to-b from-[#E3F1E7] via-[#F5F2EC] to-[#F5F2EC] flex flex-col overflow-hidden">
      <LeafSprig className="absolute top-2 -right-8 w-32 rotate-12" color="#52B788" opacity={0.28} />
      <div className="relative flex-1 w-full max-w-xl mx-auto flex flex-col">
        {mobileScreen === 'landing' && (
          <LandingScreen onStart={() => setMobileScreen('task-picker')} />
        )}
        {mobileScreen === 'task-picker' && (
          <TaskPickerScreen onSelect={handleTaskSelect} onTool={openTool} onBack={handleMobileBack} onHome={handleHome} />
        )}
        {mobileScreen === 'tool' && (
          <div className="flex flex-col min-h-dvh animate-fade-up">
            <TopBar onBack={handleMobileBack} onHome={handleHome} title={TOOLS.find((x) => x.id === tool)?.label ?? 'Tools'} />
            <div className="flex-1 px-5 pt-2 pb-10">
              <FarmTools tool={tool} focus={focus} onTool={openTool} />
            </div>
          </div>
        )}
        {mobileScreen === 'working' && (
          <>
            {panel.panelState === 'input' && (
              <div className="flex flex-col min-h-dvh animate-fade-up">
                <TopBar onBack={handleMobileBack} onHome={handleHome} title={taskMeta[task].label} />
                <div className="flex-1 px-5 pt-2 pb-10">
                  <InputMethodContent task={task} onCapture={panel.handleCapture} />
                </div>
              </div>
            )}
            {panel.panelState === 'loading' && (
              <div className="flex flex-col min-h-dvh animate-fade-in px-[clamp(1rem,5vw,1.25rem)] pt-12">
                <LoadingContent image={panel.uploadedImage} />
              </div>
            )}
            {panel.panelState === 'results' && panel.result && (
              <div className="flex flex-col min-h-dvh animate-fade-up">
                <TopBar onBack={panel.handleRetry} onHome={handleHome} title={tr('result')} />
                <div className="flex-1 overflow-y-auto px-5 pt-1 pb-10">
                  <ResultsContent
                    task={task}
                    result={panel.result}
                    onRetry={panel.handleRetry}
                    onLearn={handleLearn}
                  />
                </div>
              </div>
            )}
            {panel.panelState === 'error' && (
              <div className="flex flex-col min-h-dvh animate-fade-in">
                <div className="px-5 pt-2">
                  <ErrorContent error={panel.error} canRetrySame={panel.hasFile} onRetrySame={panel.handleRetrySame} onReset={panel.handleRetry} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  return (
    <LangProvider>
      <AppInner />
    </LangProvider>
  )
}

function AppInner() {
  const isDesktop = useIsDesktop()
  const [started, setStarted] = useState(false)
  if (isDesktop && !started) {
    return (
      <div className="bg-[#F5F2EC] min-h-dvh">
        <LandingScreen onStart={() => setStarted(true)} />
      </div>
    )
  }
  return isDesktop ? <DesktopApp onHome={() => setStarted(false)} /> : <MobileApp />
}
