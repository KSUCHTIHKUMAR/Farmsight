"""Port of src/hub/Care.tsx (CareGuide)."""
from python.h import h
from python.hub.crops import DEFICIENCIES, FERTILIZER_TYPES, crop_img
from python.hub.ui import H, act, all_crops, bullets, card, chip, display, get_crop, note, style, w

TABS = [
    {"id": "soil", "label": "Soil & irrigation"},
    {"id": "nutrients", "label": "Nutrients & fertilizer"},
    {"id": "deficiency", "label": "Deficiency symptoms"},
    {"id": "disease", "label": "Disease prevention"},
    {"id": "pests", "label": "Pest management"},
]

_LINK = "tap text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl"


class CareState:
    def __init__(self, initial_crop=None, disease_id=None):
        self.crop_id = initial_crop or "tomato"
        self.tab = "disease" if disease_id else "soil"


def _p(cls, *c):
    return h("p", {"class_": cls}, *c)


def _b(label):
    return h("span", {"class_": "font-semibold"}, label)


def care_guide(state, initial_crop=None, disease_id=None, scan_label=None):
    """onTool -> data-action="tool"; setCropId/setTab -> care-crop / care-tab."""
    crops = all_crops()
    crop = get_crop(state.crop_id) or crops[0]
    tab = state.tab
    tint = crop.tint
    D = {"style": style(display)}

    if tab == "soil":
        body = [
            card(H(f"{crop.name} soil preparation"), bullets(crop.care.soilPrep),
                 _p("text-sm text-[#3A4A38] mt-3", _b("Suitable soil: "), crop.soil, " ", _b("pH: "), f"{crop.ph}."), accent=tint),
            card(H("Irrigation"), bullets(crop.care.irrigation), _p("text-sm text-[#3A4A38] mt-3", crop.water), accent=tint),
        ]
    elif tab == "nutrients":
        body = [
            card(
                H(f"{crop.name} nutrient needs"),
                _p("text-sm text-[#3A4A38] leading-relaxed mb-3", crop.nutrients),
                bullets(crop.care.fertilizer),
                h(
                    "div",
                    {"class_": "mt-4 grid sm:grid-cols-2 gap-3 text-sm text-[#3A4A38]"},
                    h("div", {"class_": "rounded-xl bg-[#F5F2EC] p-3"},
                      h("p", {"class_": "font-bold text-[#1A201A] mb-1", **D}, "Major nutrients"),
                      h("p", None, "Nitrogen (leaf and shoot growth), phosphorus (roots and flowering), potassium (water balance and fruit quality). Also calcium, magnesium and sulphur.")),
                    h("div", {"class_": "rounded-xl bg-[#F5F2EC] p-3"},
                      h("p", {"class_": "font-bold text-[#1A201A] mb-1", **D}, "Micronutrients"),
                      h("p", None, "Zinc, iron, manganese, boron, copper and molybdenum are needed in small amounts. Apply only when a test shows a need.")),
                ),
                accent=tint,
            ),
            card(
                H("Choosing fertilizer types"),
                h("ul", {"class_": "space-y-3"}, [
                    h("li", None,
                      h("p", {"class_": "text-sm font-bold text-[#1A201A]", **D}, f.type),
                      _p("text-sm text-[#3A4A38]", f.examples),
                      _p("text-xs text-[#5A6A59]", f.note))
                    for f in w(FERTILIZER_TYPES)
                ]),
                _p("text-xs text-[#5A6A59] mt-3", "Rates, timing and split schedules should come from your soil test report and local recommendations."),
                accent=tint,
            ),
        ]
    elif tab == "deficiency":
        body = [
            card(
                H("Typical nutrient deficiency symptoms"),
                h("ul", {"class_": "space-y-3"}, [
                    h("li", {"class_": "border-b border-[#EEEAE1] last:border-0 pb-3 last:pb-0"},
                      h("p", {"class_": "text-sm font-bold text-[#1A201A]", **D}, d.nutrient),
                      _p("text-sm text-[#3A4A38]", d.symptom),
                      _p("text-xs text-[#5A6A59]", d.note))
                    for d in w(DEFICIENCIES)
                ]),
                accent=tint,
            ),
            card(H(f"Watch for in {crop.name.lower()}"), bullets(crop.watchFor), accent=tint),
            note("Symptoms overlap with disease, root damage, waterlogging, salinity and pH problems. Do not treat on appearance alone. Confirm with a soil or leaf test.", tone="warn"),
        ]
    elif tab == "disease":
        items = []
        for d in crop.diseases:
            hit = d.id == disease_id and crop.id == initial_crop
            items.append(
                h(
                    "li",
                    {
                        "data_scroll_target": True if hit else None,
                        "class_": "rounded-xl p-3 border " + ("border-[#52B788] bg-[#F3FAF5]" if hit else "border-[#EEEAE1]"),
                    },
                    h("p", {"class_": "text-sm font-bold text-[#1A201A]", **D}, d.name, " ",
                      h("span", {"class_": "font-normal italic text-[#5A6A59] text-xs"}, d.agent)),
                    _p("text-sm text-[#3A4A38] mt-1", _b("Symptoms: "), d.symptoms),
                    _p("text-sm text-[#3A4A38] mt-1", _b("Favoured by: "), d.favoured),
                    _p("text-sm text-[#3A4A38] mt-1", _b("Prevention: "), d.prevention),
                )
            )
        body = [
            card(H(f"Prevention for {crop.name.lower()}"), bullets(crop.care.prevention), accent=tint),
            card(
                H("Disease profiles"),
                h("ul", {"class_": "space-y-3"}, items),
                _p("text-xs text-[#5A6A59] mt-3", "If a crop protection product is needed, choose one registered for this crop and disease where you farm, follow the label, and seek local advice."),
                accent=tint,
            ),
        ]
    else:  # pests
        body = [
            card(H("Common pests"), bullets(crop.pests), accent=tint),
            card(H(f"Responsible management for {crop.name.lower()}"), bullets(crop.care.pests), accent=tint),
            card(
                H("Integrated pest management basics"),
                bullets([
                    "Scout regularly and identify the problem before acting.",
                    "Start with prevention: healthy planting material, rotation, sanitation and good spacing.",
                    "Use physical and biological controls where possible.",
                    "Use crop-protection products only when needed, as labelled and as locally registered, and protect pollinators and water sources.",
                ]),
                accent=tint,
            ),
        ]

    tabs = [
        h(
            "button",
            {
                **act("care-tab", tab=t["id"]),
                "role": "tab",
                "aria_selected": "true" if tab == t["id"] else "false",
                "class_": "tap whitespace-nowrap text-xs sm:text-sm font-semibold px-3.5 py-2 rounded-lg transition-colors duration-150 "
                + ("text-white" if tab == t["id"] else "bg-[#E8E4DB] text-[#3A4A38]"),
                "style": style(display, {"backgroundColor": tint}) if tab == t["id"] else style(display),
            },
            t["label"],
        )
        for t in TABS
    ]

    return h(
        "div",
        {"class_": "space-y-4"},
        note("Test your soil before choosing fertilizer. This guide gives no fixed doses because needs depend on soil, cultivar and climate. Confirm plans with your local agricultural extension service, and use only products registered for the crop in your country.", tone="warn"),
        note(f"From your scan: the AI suggested “{scan_label}”. This is a possible diagnosis, not a confirmed one. Compare the symptoms below with your plant and seek expert confirmation.") if scan_label else None,
        h("div", {"class_": "flex gap-2 overflow-x-auto pb-1 -mx-1 px-1", "role": "group", "aria_label": "Choose crop"},
          [chip(c.id == state.crop_id, c.name, action="care-crop", crop_id=c.id) for c in crops]),
        h("div", {"role": "tablist", "aria_label": "Care topics", "class_": "flex gap-2 overflow-x-auto pb-1 -mx-1 px-1"}, tabs),
        h(
            "div",
            {"class_": "flex items-center gap-3 rounded-2xl px-3 py-2.5", "style": style({"backgroundColor": crop.tintBg})},
            h("img", {"src": crop_img(crop.id, 160, 160), "alt": "", "class_": "w-12 h-12 rounded-xl object-cover"}),
            h("div", None,
              h("p", {"class_": "font-extrabold", "style": style(display, {"color": tint})}, crop.name),
              _p("text-xs text-[#3A4A38]", f"{crop.group} · pH {crop.ph.replace('About ', '')}")),
        ),
        h("div", {"class_": "space-y-4 animate-fade-in", "role": "tabpanel"}, body),
        h(
            "div",
            {"class_": "flex flex-wrap gap-2"},
            h("button", {**act("tool", tool="hub", crop_id=crop.id), "class_": _LINK, **D}, f"Open {crop.name.lower()} profile"),
            h("button", {**act("tool", tool="calendar", crop_id=crop.id), "class_": _LINK, **D}, "Plan a calendar"),
        ),
    )
