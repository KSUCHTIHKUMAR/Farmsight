"""Port of src/hub/Hub.tsx (KnowledgeHub)."""
from python.h import h
from python.hub.crops import ABOUT_TIMINGS, crop_img
from python.hub.ui import (H, act, all_crops, bullets, card, chip, display, input_cls, note, pill, style)

TABS = [
    {"id": "overview", "label": "Overview"},
    {"id": "growing", "label": "Growing needs"},
    {"id": "stages", "label": "Growth stages"},
    {"id": "problems", "label": "Pests & problems"},
    {"id": "harvest", "label": "Harvest & storage"},
    {"id": "nutrition", "label": "Nutrition & uses"},
]


class HubState:
    """useState bundle. initial_crop mirrors the initialCrop prop; tab is the Profile tab."""

    def __init__(self, initial_crop=None):
        self.q = ""
        self.group = "All"
        self.open = initial_crop
        self.tab = "overview"


def matches(c, q):
    hay = " ".join([c.name, c.botanical, *c.aliases, *c.pests, *[d.name for d in c.diseases], *c.uses, *c.types]).lower()
    return all(wd in hay for wd in q.lower().split())


def row(k, v):
    return h(
        "div",
        {"class_": "py-2.5 border-b border-[#EEEAE1] last:border-0 sm:grid sm:grid-cols-[9rem_1fr] sm:gap-4"},
        h("dt", {"class_": "text-xs font-bold uppercase tracking-wide text-[#5A6A59] mb-0.5 sm:mb-0 sm:pt-0.5"}, k),
        h("dd", {"class_": "text-sm text-[#3A4A38] leading-relaxed"}, v),
    )


_LINK_BTN = "tap mt-4 text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-2 rounded-xl"


def profile(crop, state):
    """onBack -> data-action="hub-back"; onTool -> data-action="tool" data-tool/data-crop-id."""
    tab = state.tab
    tint = crop.tint
    if tab == "overview":
        body = [
            card(H("Varieties and crop types"), bullets(crop.types), accent=tint),
            card(
                H("Typical maturity"),
                h("p", {"class_": "text-sm text-[#3A4A38] leading-relaxed"}, crop.maturity),
                h("p", {"class_": "text-xs text-[#5A6A59] mt-2"}, ABOUT_TIMINGS),
                accent=tint,
            ),
        ]
    elif tab == "growing":
        body = [
            card(
                H("Growing conditions"),
                h(
                    "dl",
                    None,
                    row("Climate", crop.climate),
                    row("Seasons", crop.seasons),
                    row("Soil", crop.soil),
                    row("Soil pH", crop.ph),
                    row("Sunlight", crop.sun),
                    row("Irrigation", crop.water),
                    row("Nutrients", crop.nutrients),
                ),
                h(
                    "div",
                    {"class_": "mt-4"},
                    note("General guidance only. Local climate, cultivar and soil change what works. Test your soil and ask your local agriculture office.", tone="warn"),
                ),
                accent=tint,
            )
        ]
    elif tab == "stages":
        body = [
            card(
                H("Growth stages (approximate)"),
                h(
                    "ol",
                    {"class_": "space-y-3"},
                    [
                        h(
                            "li",
                            {"class_": "flex gap-3"},
                            h("span", {"class_": "w-7 h-7 rounded-full bg-[#D8EFDF] text-[#2D6A4F] text-xs font-bold flex items-center justify-center flex-shrink-0", "style": style(display)}, i + 1),
                            h(
                                "div",
                                None,
                                h("p", {"class_": "text-sm font-bold text-[#1A201A]", "style": style(display)}, s.name),
                                h("p", {"class_": "text-sm text-[#3A4A38]"}, s.note),
                            ),
                        )
                        for i, s in enumerate(crop.stages)
                    ],
                ),
                h("p", {"class_": "text-sm text-[#3A4A38] mt-4"}, h("span", {"class_": "font-semibold"}, "Maturity: "), crop.maturity),
                h("div", {"class_": "mt-3"}, note(ABOUT_TIMINGS, tone="warn")),
                h("button", {**act("tool", tool="calendar", crop_id=crop.id), "class_": _LINK_BTN, "style": style(display)}, f"Plan a calendar for {crop.name.lower()}"),
                accent=tint,
            )
        ]
    elif tab == "problems":
        body = [
            card(
                H("Common pests"),
                h("div", {"class_": "flex flex-wrap gap-1.5"}, [pill(p, color="#8A4A1C", bg="#FDE8D8") for p in crop.pests]),
                accent=tint,
            ),
            card(
                H("Common diseases"),
                h(
                    "ul",
                    {"class_": "space-y-4"},
                    [
                        h(
                            "li",
                            None,
                            h("p", {"class_": "text-sm font-bold text-[#1A201A]", "style": style(display)}, d.name),
                            h("p", {"class_": "text-sm text-[#3A4A38] mt-0.5"}, h("span", {"class_": "font-semibold"}, "Look for: "), d.symptoms),
                        )
                        for d in crop.diseases
                    ],
                ),
                h("button", {**act("tool", tool="care", crop_id=crop.id), "class_": _LINK_BTN, "style": style(display)}, "Prevention in the Crop Care Guide"),
                accent=tint,
            ),
            card(
                H("Deficiency symptoms to watch for"),
                bullets(crop.watchFor),
                h("p", {"class_": "text-xs text-[#5A6A59] mt-3"}, "Similar symptoms can come from disease, waterlogging, salt or pH problems. Confirm with a soil or leaf test."),
                accent=tint,
            ),
        ]
    elif tab == "harvest":
        body = [
            card(H("Harvest indicators"), bullets(crop.harvest), accent=tint),
            card(H("Storage and post-harvest handling"), bullets(crop.storage), accent=tint),
        ]
    else:  # nutrition
        body = [
            card(
                H("Nutritional highlights"),
                h("div", {"class_": "flex flex-wrap gap-1.5 mb-3"}, [pill(x) for x in crop.nutrition.highlights]),
                h("p", {"class_": "text-sm text-[#3A4A38]"}, f"About {crop.nutrition.kcal} kcal per 100 g raw edible portion (USDA FoodData Central reference, rounded)."),
                h("p", {"class_": "text-xs text-[#5A6A59] mt-2"}, "Values vary with cultivar and ripeness. This is general information, not dietary advice."),
                accent=tint,
            ),
            card(H("Common culinary uses"), bullets(crop.uses), accent=tint),
        ]

    tabs = []
    for t in TABS:
        on = tab == t["id"]
        tabs.append(
            h(
                "button",
                {
                    **act("hub-tab", tab=t["id"]),
                    "role": "tab",
                    "aria_selected": "true" if on else "false",
                    "class_": "tap whitespace-nowrap text-sm font-semibold px-4 py-2 rounded-full border transition-colors duration-150 "
                    + ("text-white" if on else "bg-white text-[#3A4A38] border-[#DDD8CE] hover:border-[#52B788]"),
                    "style": style(display, {"backgroundColor": tint, "borderColor": tint}) if on else style(display),
                },
                t["label"],
            )
        )

    return h(
        "div",
        {"class_": "space-y-4 animate-fade-in"},
        h(
            "button",
            {**act("hub-back"), "class_": "tap text-sm font-semibold text-[#2D6A4F] flex items-center gap-1"},
            h("span", {"aria_hidden": "true"}, "←"),
            " All crops",
        ),
        h(
            "div",
            {"class_": "relative rounded-2xl overflow-hidden min-h-[11rem] sm:min-h-[14rem] flex items-end", "style": style({"backgroundColor": tint})},
            h("img", {"src": crop_img(crop.id, 1000, 500), "alt": crop.name, "class_": "absolute inset-0 w-full h-full object-cover"}),
            h("div", {"class_": "absolute inset-0", "style": style({"background": f"linear-gradient(to top, {tint}F0 0%, {tint}66 45%, transparent 100%)"})}),
            h(
                "div",
                {"class_": "relative p-4 sm:p-6 text-white"},
                h("span", {"class_": "inline-block text-[11px] font-bold uppercase tracking-wider bg-white/90 rounded-full px-2.5 py-0.5 mb-2", "style": style({"color": tint})}, crop.group),
                h("h2", {"class_": "text-3xl font-extrabold", "style": style(display)}, crop.name),
                h("p", {"class_": "text-xs italic text-white/85"}, crop.botanical),
                h("p", {"class_": "text-xs text-white/85 mt-0.5"}, "Also called: " + ", ".join(crop.aliases)),
            ),
        ),
        h("div", {"role": "tablist", "aria_label": f"{crop.name} sections", "class_": "flex gap-2 overflow-x-auto pb-1 -mx-1 px-1"}, tabs),
        h("div", {"class_": "space-y-4 animate-fade-in", "role": "tabpanel"}, body),
    )


def knowledge_hub(state):
    crops = all_crops()
    crop = next((c for c in crops if c.id == state.open), None)
    if crop:
        return profile(crop, state)

    lst = [c for c in crops if (state.group == "All" or c.group == state.group) and matches(c, state.q)]
    n = len(lst)
    q = state.q

    if n == 0:
        results = card(h("p", {"class_": "text-sm text-[#3A4A38]"}, f"No crops match “{q}”. Try a different word or clear the filter."))
    else:
        results = h(
            "div",
            {"class_": "grid grid-cols-2 xl:grid-cols-3 gap-3"},
            [
                h(
                    "button",
                    {
                        **act("hub-open", crop_id=c.id),
                        "class_": "card-lift group text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] rounded-2xl overflow-hidden",
                        "style": style({"borderBottom": f"4px solid {c.tint}"}),
                    },
                    h(
                        "div",
                        {"class_": "relative aspect-[4/3] overflow-hidden", "style": style({"backgroundColor": c.tintBg})},
                        h("img", {"src": crop_img(c.id, 500, 375), "alt": "", "loading": "lazy", "class_": "absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"}),
                        h("span", {"class_": "absolute top-2 left-2 text-[11px] font-bold rounded-full px-2.5 py-0.5", "style": style({"backgroundColor": c.tintBg, "color": c.tint})}, c.group),
                    ),
                    h(
                        "div",
                        {"class_": "p-3"},
                        h("p", {"class_": "font-extrabold text-[#1A201A]", "style": style(display)}, c.name),
                        h("p", {"class_": "text-xs text-[#5A6A59] truncate"}, f"{c.aliases[0]} · pH {c.ph.replace('About ', '')}"),
                    ),
                )
                for c in lst
            ],
        )

    return h(
        "div",
        {"class_": "space-y-4"},
        h("input", {**act("hub-search"), "type": "search", "aria_label": "Search crops", "class_": input_cls, "placeholder": "Search e.g. blight, thrips, pickle, mango", "value": q}),
        h(
            "div",
            {"class_": "flex gap-2 flex-wrap", "role": "group", "aria_label": "Filter by type"},
            [chip(state.group == g, "All" if g == "All" else g + "s", action="hub-group", group=g) for g in ("All", "Vegetable", "Fruit", "Field crop")],
        ),
        h("p", {"class_": "text-xs text-[#5A6A59]", "aria_live": "polite"}, f"{n} {'crop' if n == 1 else 'crops'} shown"),
        results,
    )
