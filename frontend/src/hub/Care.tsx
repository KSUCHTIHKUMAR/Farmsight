import { useEffect, useRef, useState } from 'react'
import { CROPS, DEFICIENCIES, FERTILIZER_TYPES, getCrop } from './crops'
import { cropImg } from './crops'
import { Bullets, Card as BaseCard, Chip, H, Note, display, type ToolId } from './ui'

const Card = BaseCard

type Tab = 'soil' | 'nutrients' | 'deficiency' | 'disease' | 'pests'
const TABS: { id: Tab; label: string }[] = [
  { id: 'soil', label: 'Soil & irrigation' },
  { id: 'nutrients', label: 'Nutrients & fertilizer' },
  { id: 'deficiency', label: 'Deficiency symptoms' },
  { id: 'disease', label: 'Disease prevention' },
  { id: 'pests', label: 'Pest management' },
]

export default function CareGuide({
  initialCrop,
  diseaseId,
  scanLabel,
  onTool,
}: {
  initialCrop?: string
  diseaseId?: string
  scanLabel?: string
  onTool: (t: ToolId, cropId?: string) => void
}) {
  const [cropId, setCropId] = useState(initialCrop ?? 'tomato')
  const [tab, setTab] = useState<Tab>(diseaseId ? 'disease' : 'soil')
  const crop = getCrop(cropId) ?? CROPS[0]
  const target = useRef<HTMLLIElement | null>(null)

  useEffect(() => {
    if (diseaseId) target.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [diseaseId])

  return (
    <div className="space-y-4">
      <Note tone="warn">
        Test your soil before choosing fertilizer. This guide gives no fixed doses because needs depend on soil, cultivar and
        climate. Confirm plans with your local agricultural extension service, and use only products registered for the crop in your country.
      </Note>
      {scanLabel && (
        <Note>
          From your scan: the AI suggested &ldquo;{scanLabel}&rdquo;. This is a possible diagnosis, not a confirmed one. Compare the symptoms below with your plant and seek expert confirmation.
        </Note>
      )}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1" role="group" aria-label="Choose crop">
        {CROPS.map((c) => <Chip key={c.id} on={c.id === cropId} onClick={() => setCropId(c.id)}>{c.name}</Chip>)}
      </div>
      <div role="tablist" aria-label="Care topics" className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`tap whitespace-nowrap text-xs sm:text-sm font-semibold px-3.5 py-2 rounded-lg transition-colors duration-150 ${tab === t.id ? 'text-white' : 'bg-[#E8E4DB] text-[#3A4A38]'}`}
            style={tab === t.id ? { ...display, backgroundColor: crop.tint } : display}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3 rounded-2xl px-3 py-2.5" style={{ backgroundColor: crop.tintBg }}>
        <img src={cropImg(crop.id, 160, 160)} alt="" className="w-12 h-12 rounded-xl object-cover" />
        <div>
          <p className="font-extrabold" style={{ ...display, color: crop.tint }}>{crop.name}</p>
          <p className="text-xs text-[#3A4A38]">{crop.group} · pH {crop.ph.replace('About ', '')}</p>
        </div>
      </div>
      <div key={`${crop.id}-${tab}`} className="space-y-4 animate-fade-in" role="tabpanel">
        {tab === 'soil' && (
          <>
            <Card accent={crop.tint}><H>{crop.name} soil preparation</H><Bullets items={crop.care.soilPrep} /><p className="text-sm text-[#3A4A38] mt-3"><span className="font-semibold">Suitable soil: </span>{crop.soil} <span className="font-semibold">pH: </span>{crop.ph}.</p></Card>
            <Card accent={crop.tint}><H>Irrigation</H><Bullets items={crop.care.irrigation} /><p className="text-sm text-[#3A4A38] mt-3">{crop.water}</p></Card>
          </>
        )}
        {tab === 'nutrients' && (
          <>
            <Card accent={crop.tint}>
              <H>{crop.name} nutrient needs</H>
              <p className="text-sm text-[#3A4A38] leading-relaxed mb-3">{crop.nutrients}</p>
              <Bullets items={crop.care.fertilizer} />
              <div className="mt-4 grid sm:grid-cols-2 gap-3 text-sm text-[#3A4A38]">
                <div className="rounded-xl bg-[#F5F2EC] p-3"><p className="font-bold text-[#1A201A] mb-1" style={display}>Major nutrients</p><p>Nitrogen (leaf and shoot growth), phosphorus (roots and flowering), potassium (water balance and fruit quality). Also calcium, magnesium and sulphur.</p></div>
                <div className="rounded-xl bg-[#F5F2EC] p-3"><p className="font-bold text-[#1A201A] mb-1" style={display}>Micronutrients</p><p>Zinc, iron, manganese, boron, copper and molybdenum are needed in small amounts. Apply only when a test shows a need.</p></div>
              </div>
            </Card>
            <Card accent={crop.tint}>
              <H>Choosing fertilizer types</H>
              <ul className="space-y-3">
                {FERTILIZER_TYPES.map((f) => (
                  <li key={f.type}>
                    <p className="text-sm font-bold text-[#1A201A]" style={display}>{f.type}</p>
                    <p className="text-sm text-[#3A4A38]">{f.examples}</p>
                    <p className="text-xs text-[#5A6A59]">{f.note}</p>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-[#5A6A59] mt-3">Rates, timing and split schedules should come from your soil test report and local recommendations.</p>
            </Card>
          </>
        )}
        {tab === 'deficiency' && (
          <>
            <Card accent={crop.tint}>
              <H>Typical nutrient deficiency symptoms</H>
              <ul className="space-y-3">
                {DEFICIENCIES.map((d) => (
                  <li key={d.nutrient} className="border-b border-[#EEEAE1] last:border-0 pb-3 last:pb-0">
                    <p className="text-sm font-bold text-[#1A201A]" style={display}>{d.nutrient}</p>
                    <p className="text-sm text-[#3A4A38]">{d.symptom}</p>
                    <p className="text-xs text-[#5A6A59]">{d.note}</p>
                  </li>
                ))}
              </ul>
            </Card>
            <Card accent={crop.tint}><H>Watch for in {crop.name.toLowerCase()}</H><Bullets items={crop.watchFor} /></Card>
            <Note tone="warn">Symptoms overlap with disease, root damage, waterlogging, salinity and pH problems. Do not treat on appearance alone. Confirm with a soil or leaf test.</Note>
          </>
        )}
        {tab === 'disease' && (
          <>
            <Card accent={crop.tint}><H>Prevention for {crop.name.toLowerCase()}</H><Bullets items={crop.care.prevention} /></Card>
            <Card accent={crop.tint}>
              <H>Disease profiles</H>
              <ul className="space-y-3">
                {crop.diseases.map((d) => {
                  const hit = d.id === diseaseId && crop.id === initialCrop
                  return (
                    <li key={d.id} ref={hit ? target : undefined} className={`rounded-xl p-3 border ${hit ? 'border-[#52B788] bg-[#F3FAF5]' : 'border-[#EEEAE1]'}`}>
                      <p className="text-sm font-bold text-[#1A201A]" style={display}>{d.name} <span className="font-normal italic text-[#5A6A59] text-xs">{d.agent}</span></p>
                      <p className="text-sm text-[#3A4A38] mt-1"><span className="font-semibold">Symptoms: </span>{d.symptoms}</p>
                      <p className="text-sm text-[#3A4A38] mt-1"><span className="font-semibold">Favoured by: </span>{d.favoured}</p>
                      <p className="text-sm text-[#3A4A38] mt-1"><span className="font-semibold">Prevention: </span>{d.prevention}</p>
                    </li>
                  )
                })}
              </ul>
              <p className="text-xs text-[#5A6A59] mt-3">If a crop protection product is needed, choose one registered for this crop and disease where you farm, follow the label, and seek local advice.</p>
            </Card>
          </>
        )}
        {tab === 'pests' && (
          <>
            <Card accent={crop.tint}><H>Common pests</H><Bullets items={crop.pests} /></Card>
            <Card accent={crop.tint}><H>Responsible management for {crop.name.toLowerCase()}</H><Bullets items={crop.care.pests} /></Card>
            <Card accent={crop.tint}>
              <H>Integrated pest management basics</H>
              <Bullets items={['Scout regularly and identify the problem before acting.', 'Start with prevention: healthy planting material, rotation, sanitation and good spacing.', 'Use physical and biological controls where possible.', 'Use crop-protection products only when needed, as labelled and as locally registered, and protect pollinators and water sources.']} />
            </Card>
          </>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => onTool('hub', crop.id)} className="tap text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl" style={display}>Open {crop.name.toLowerCase()} profile</button>
        <button onClick={() => onTool('calendar', crop.id)} className="tap text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl" style={display}>Plan a calendar</button>
      </div>
    </div>
  )
}
