import { useMemo, useState } from 'react'
import { ABOUT_TIMINGS, CROPS, type Crop } from './crops'
import { cropImg } from './crops'
import { Bullets, Card as BaseCard, Chip, H, Note, Pill, display, inputCls, type ToolId } from './ui'

const Card = BaseCard

type Tab = 'overview' | 'growing' | 'stages' | 'problems' | 'harvest' | 'nutrition'
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'growing', label: 'Growing needs' },
  { id: 'stages', label: 'Growth stages' },
  { id: 'problems', label: 'Pests & problems' },
  { id: 'harvest', label: 'Harvest & storage' },
  { id: 'nutrition', label: 'Nutrition & uses' },
]

function matches(c: Crop, q: string) {
  const hay = [c.name, c.botanical, ...c.aliases, ...c.pests, ...c.diseases.map((d) => d.name), ...c.uses, ...c.types].join(' ').toLowerCase()
  return q
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((w) => hay.includes(w))
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="py-2.5 border-b border-[#EEEAE1] last:border-0 sm:grid sm:grid-cols-[9rem_1fr] sm:gap-4">
      <dt className="text-xs font-bold uppercase tracking-wide text-[#5A6A59] mb-0.5 sm:mb-0 sm:pt-0.5">{k}</dt>
      <dd className="text-sm text-[#3A4A38] leading-relaxed">{v}</dd>
    </div>
  )
}

function Profile({ crop, onBack, onTool }: { crop: Crop; onBack: () => void; onTool: (t: ToolId, cropId?: string) => void }) {
  const [tab, setTab] = useState<Tab>('overview')
  return (
    <div className="space-y-4 animate-fade-in">
      <button onClick={onBack} className="tap text-sm font-semibold text-[#2D6A4F] flex items-center gap-1">
        <span aria-hidden>←</span> All crops
      </button>
      <div className="relative rounded-2xl overflow-hidden min-h-[11rem] sm:min-h-[14rem] flex items-end" style={{ backgroundColor: crop.tint }}>
        <img src={cropImg(crop.id, 1000, 500)} alt={crop.name} className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0" style={{ background: `linear-gradient(to top, ${crop.tint}F0 0%, ${crop.tint}66 45%, transparent 100%)` }} />
        <div className="relative p-4 sm:p-6 text-white">
          <span className="inline-block text-[11px] font-bold uppercase tracking-wider bg-white/90 rounded-full px-2.5 py-0.5 mb-2" style={{ color: crop.tint }}>{crop.group}</span>
          <h2 className="text-3xl font-extrabold" style={display}>{crop.name}</h2>
          <p className="text-xs italic text-white/85">{crop.botanical}</p>
          <p className="text-xs text-white/85 mt-0.5">Also called: {crop.aliases.join(', ')}</p>
        </div>
      </div>
      <div role="tablist" aria-label={`${crop.name} sections`} className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={`tap whitespace-nowrap text-sm font-semibold px-4 py-2 rounded-full border transition-colors duration-150 ${
              tab === t.id ? 'text-white' : 'bg-white text-[#3A4A38] border-[#DDD8CE] hover:border-[#52B788]'
            }`}
            style={tab === t.id ? { ...display, backgroundColor: crop.tint, borderColor: crop.tint } : display}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div key={tab} className="space-y-4 animate-fade-in" role="tabpanel">
        {tab === 'overview' && (
          <>
            <Card accent={crop.tint}>
              <H>Varieties and crop types</H>
              <Bullets items={crop.types} />
            </Card>
            <Card accent={crop.tint}>
              <H>Typical maturity</H>
              <p className="text-sm text-[#3A4A38] leading-relaxed">{crop.maturity}</p>
              <p className="text-xs text-[#5A6A59] mt-2">{ABOUT_TIMINGS}</p>
            </Card>
          </>
        )}
        {tab === 'growing' && (
          <Card accent={crop.tint}>
            <H>Growing conditions</H>
            <dl>
              <Row k="Climate" v={crop.climate} />
              <Row k="Seasons" v={crop.seasons} />
              <Row k="Soil" v={crop.soil} />
              <Row k="Soil pH" v={crop.ph} />
              <Row k="Sunlight" v={crop.sun} />
              <Row k="Irrigation" v={crop.water} />
              <Row k="Nutrients" v={crop.nutrients} />
            </dl>
            <div className="mt-4">
              <Note tone="warn">General guidance only. Local climate, cultivar and soil change what works. Test your soil and ask your local agriculture office.</Note>
            </div>
          </Card>
        )}
        {tab === 'stages' && (
          <Card accent={crop.tint}>
            <H>Growth stages (approximate)</H>
            <ol className="space-y-3">
              {crop.stages.map((s, i) => (
                <li key={s.name} className="flex gap-3">
                  <span className="w-7 h-7 rounded-full bg-[#D8EFDF] text-[#2D6A4F] text-xs font-bold flex items-center justify-center flex-shrink-0" style={display}>{i + 1}</span>
                  <div>
                    <p className="text-sm font-bold text-[#1A201A]" style={display}>{s.name}</p>
                    <p className="text-sm text-[#3A4A38]">{s.note}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="text-sm text-[#3A4A38] mt-4"><span className="font-semibold">Maturity: </span>{crop.maturity}</p>
            <div className="mt-3"><Note tone="warn">{ABOUT_TIMINGS}</Note></div>
            <button onClick={() => onTool('calendar', crop.id)} className="tap mt-4 text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl" style={display}>
              Plan a calendar for {crop.name.toLowerCase()}
            </button>
          </Card>
        )}
        {tab === 'problems' && (
          <>
            <Card accent={crop.tint}>
              <H>Common pests</H>
              <div className="flex flex-wrap gap-1.5">{crop.pests.map((p) => <Pill key={p} color="#8A4A1C" bg="#FDE8D8">{p}</Pill>)}</div>
            </Card>
            <Card accent={crop.tint}>
              <H>Common diseases</H>
              <ul className="space-y-4">
                {crop.diseases.map((d) => (
                  <li key={d.id}>
                    <p className="text-sm font-bold text-[#1A201A]" style={display}>{d.name}</p>
                    <p className="text-sm text-[#3A4A38] mt-0.5"><span className="font-semibold">Look for: </span>{d.symptoms}</p>
                  </li>
                ))}
              </ul>
              <button onClick={() => onTool('care', crop.id)} className="tap mt-4 text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl" style={display}>
                Prevention in the Crop Care Guide
              </button>
            </Card>
            <Card accent={crop.tint}>
              <H>Deficiency symptoms to watch for</H>
              <Bullets items={crop.watchFor} />
              <p className="text-xs text-[#5A6A59] mt-3">Similar symptoms can come from disease, waterlogging, salt or pH problems. Confirm with a soil or leaf test.</p>
            </Card>
          </>
        )}
        {tab === 'harvest' && (
          <>
            <Card accent={crop.tint}><H>Harvest indicators</H><Bullets items={crop.harvest} /></Card>
            <Card accent={crop.tint}><H>Storage and post-harvest handling</H><Bullets items={crop.storage} /></Card>
          </>
        )}
        {tab === 'nutrition' && (
          <>
            <Card accent={crop.tint}>
              <H>Nutritional highlights</H>
              <div className="flex flex-wrap gap-1.5 mb-3">{crop.nutrition.highlights.map((h) => <Pill key={h}>{h}</Pill>)}</div>
              <p className="text-sm text-[#3A4A38]">About {crop.nutrition.kcal} kcal per 100 g raw edible portion (USDA FoodData Central reference, rounded).</p>
              <p className="text-xs text-[#5A6A59] mt-2">Values vary with cultivar and ripeness. This is general information, not dietary advice.</p>
            </Card>
            <Card accent={crop.tint}><H>Common culinary uses</H><Bullets items={crop.uses} /></Card>
          </>
        )}
      </div>
    </div>
  )
}

export default function KnowledgeHub({ initialCrop, onTool }: { initialCrop?: string; onTool: (t: ToolId, cropId?: string) => void }) {
  const [q, setQ] = useState('')
  const [group, setGroup] = useState<'All' | 'Vegetable' | 'Fruit' | 'Field crop'>('All')
  const [open, setOpen] = useState<string | null>(initialCrop ?? null)
  const list = useMemo(() => CROPS.filter((c) => (group === 'All' || c.group === group) && matches(c, q)), [q, group])
  const crop = CROPS.find((c) => c.id === open)

  if (crop) return <Profile crop={crop} onBack={() => setOpen(null)} onTool={onTool} />

  return (
    <div className="space-y-4">
      <input type="search" aria-label="Search crops" className={inputCls} placeholder="Search e.g. blight, thrips, pickle, mango" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="flex gap-2 flex-wrap" role="group" aria-label="Filter by type">
        {(['All', 'Vegetable', 'Fruit', 'Field crop'] as const).map((g) => <Chip key={g} on={group === g} onClick={() => setGroup(g)}>{g === 'All' ? 'All' : g + 's'}</Chip>)}
      </div>
      <p className="text-xs text-[#5A6A59]" aria-live="polite">{list.length} {list.length === 1 ? 'crop' : 'crops'} shown</p>
      {list.length === 0 ? (
        <Card><p className="text-sm text-[#3A4A38]">No crops match &ldquo;{q}&rdquo;. Try a different word or clear the filter.</p></Card>
      ) : (
        <div className="grid grid-cols-2 xl:grid-cols-3 gap-3">
          {list.map((c) => (
            <button key={c.id} onClick={() => setOpen(c.id)} className="card-lift group text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] rounded-2xl overflow-hidden" style={{ borderBottom: `4px solid ${c.tint}` }}>
              <div className="relative aspect-[4/3] overflow-hidden" style={{ backgroundColor: c.tintBg }}>
                <img src={cropImg(c.id, 500, 375)} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
                <span className="absolute top-2 left-2 text-[11px] font-bold rounded-full px-2.5 py-0.5" style={{ backgroundColor: c.tintBg, color: c.tint }}>{c.group}</span>
              </div>
              <div className="p-3">
                <p className="font-extrabold text-[#1A201A]" style={display}>{c.name}</p>
                <p className="text-xs text-[#5A6A59] truncate">{c.aliases[0]} · pH {c.ph.replace('About ', '')}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
