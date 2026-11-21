import CalendarView from './CalendarView'
import CareGuide from './Care'
import KnowledgeHub from './Hub'
import Journal from './Journal'
import Overview from './Overview'
import { TOOLS, ToolBanner, type ToolId } from './ui'
import { useT } from '../lib/i18n'

export interface ToolFocus {
  cropId?: string
  diseaseId?: string
  scanLabel?: string
}

export default function FarmTools({
  tool,
  focus,
  onTool,
  onScan,
}: {
  tool: ToolId
  focus: ToolFocus
  onTool: (t: ToolId, cropId?: string) => void
  onScan?: (t: 'leaf' | 'produce' | 'pest') => void
}) {
  const { t } = useT()
  const meta = TOOLS.find((t) => t.id === tool)!
  const labels: Record<ToolId, string> = {
    overview: t('farmOverview'),
    hub: t('knowledgeHub'),
    care: t('cropCareGuide'),
    calendar: t('cropCalendar'),
    journal: t('farmJournal'),
  }
  const subtitles: Record<ToolId, string> = {
    overview: t('tasksAndShortcuts'),
    hub: t('cropProfilesSearch'),
    care: t('soilNutrientsPrevention'),
    calendar: t('stagesAndTasks'),
    journal: t('recordsAndScans'),
  }
  const key = `${tool}-${focus.cropId ?? ''}-${focus.diseaseId ?? ''}`
  return (
    <div key={key}>
      <ToolBanner tool={tool} title={labels[tool] || meta.label} subtitle={subtitles[tool] || meta.subtitle} />
      {tool === 'overview' && <Overview onTool={onTool} onScan={onScan} />}
      {tool === 'hub' && <KnowledgeHub initialCrop={focus.cropId} onTool={onTool} />}
      {tool === 'care' && <CareGuide initialCrop={focus.cropId} diseaseId={focus.diseaseId} scanLabel={focus.scanLabel} onTool={onTool} />}
      {tool === 'calendar' && <CalendarView initialCrop={focus.cropId} />}
      {tool === 'journal' && <Journal />}
    </div>
  )
}
