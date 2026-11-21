"""Port of src/hub/Overview.tsx."""
from python.h import h
from python.hub.crops import crop_img
from python.hub.ui import H, act, all_crops, card, display, get_crop, pill, style, tool_icon, w

from python.hub.calendar_view import as_plan
from python.hub.planner import flatten_plan, fmt_date, today_iso


def overview(plans, show_scan=True):
    """plans: useStored(PLANS_KEY) value. onTool -> data-action="tool"; onScan -> data-action="scan"."""
    today = today_iso()
    tasks = []
    for p in plans:
        c = get_crop(w(p).crop_id)
        if c:
            tasks.extend(w(t) for t in flatten_plan(as_plan(p), c._raw))
    upcoming = sorted([t for t in tasks if not t.done], key=lambda t: t.due)[:4]
    crops = all_crops()
    shortcuts = [next(c for c in crops if c.id == i) for i in ("tomato", "potato", "mango", "banana")]
    D = {"style": style(display)}

    scan = None
    if show_scan:
        scan = h(
            "div",
            {"class_": "grid grid-cols-1 sm:grid-cols-2 gap-3"},
            h("button", {**act("scan", task="leaf"), "class_": "card-lift text-left bg-[#2D6A4F] text-white rounded-2xl p-5"},
              h("p", {"class_": "text-lg font-extrabold", **D}, "Diagnose Leaf"),
              h("p", {"class_": "text-sm text-white/75"}, "Scan leaves from 12 crops for disease.")),
            h("button", {**act("scan", task="produce"), "class_": "card-lift text-left bg-[#E07B39] text-white rounded-2xl p-5"},
              h("p", {"class_": "text-lg font-extrabold", **D}, "Grade Produce"),
              h("p", {"class_": "text-sm text-white/80"}, "Grade 14 kinds of produce for freshness.")),
            h("button", {**act("scan", task="pest"), "class_": "card-lift text-left bg-[#8A4A1C] text-white rounded-2xl p-5 sm:col-span-2"},
              h("p", {"class_": "text-lg font-extrabold", **D}, "Identify Pest"),
              h("p", {"class_": "text-sm text-white/80"}, "Identify common tomato pests from a close-up photo.")),
        )

    if not upcoming:
        task_body = h("p", {"class_": "text-sm text-[#5A6A59]"}, "No tasks yet. Create a crop plan in the Crop Calendar to see what is due next.")
    else:
        task_body = h(
            "ul", {"class_": "space-y-2"},
            [
                h("li", {"class_": "flex items-center justify-between gap-3 text-sm"},
                  h("span", {"class_": "min-w-0 truncate text-[#1A201A]"},
                    h("span", {"class_": "font-semibold"}, (get_crop(t.crop_id).name if get_crop(t.crop_id) else "")),
                    f" · {t.title}"),
                  pill("Overdue", color="#C83232", bg="#FCE4E4") if t.due < today
                  else h("span", {"class_": "text-xs text-[#5A6A59] whitespace-nowrap"}, fmt_date(t.due)))
                for t in upcoming
            ],
        )

    return h(
        "div",
        {"class_": "space-y-4"},
        scan,
        h("button", {**act("tool", tool="hub"), "class_": "card-lift w-full text-left bg-white border-2 border-[#DDD8CE] hover:border-[#52B788] rounded-2xl p-4 flex items-center gap-3"},
          h("img", {"src": crop_img("vineyard", 120, 120), "alt": "", "class_": "w-11 h-11 rounded-xl object-cover"}),
          h("div", {"class_": "flex-1"},
            h("p", {"class_": "font-bold text-[#1A201A]", **D}, "Knowledge Hub"),
            h("p", {"class_": "text-xs text-[#5A6A59]"}, "Search 19 fruit, vegetable and field crop profiles."))),
        card(
            h("div", {"class_": "flex items-center justify-between mb-3"},
              H("Upcoming crop tasks"),
              h("button", {**act("tool", tool="calendar"), "class_": "text-xs font-semibold text-[#2B6A8F]"}, "Open calendar")),
            task_body,
            accent="#2B6A8F",
        ),
        card(
            H("Learn and record"),
            h(
                "div", {"class_": "grid grid-cols-2 gap-2"},
                [
                    h("button", {**act("tool", tool="hub", crop_id=c.id),
                                 "class_": "tap flex items-center gap-2 text-left rounded-xl p-1.5 pr-3 text-sm font-semibold",
                                 "style": style({"backgroundColor": c.tintBg, "color": c.tint}, display)},
                      h("img", {"src": crop_img(c.id, 120, 120), "alt": "", "class_": "w-9 h-9 rounded-lg object-cover"}),
                      c.name)
                    for c in shortcuts
                ],
                h("button", {**act("tool", tool="care"), "class_": "tap flex items-center gap-2 text-left rounded-xl px-3 py-2.5 text-sm font-semibold bg-[#F3E6D3] text-[#8A5A22]", **D},
                  tool_icon("care"), "Crop Care Guide"),
                h("button", {**act("tool", tool="journal"), "class_": "tap flex items-center gap-2 text-left rounded-xl px-3 py-2.5 text-sm font-semibold bg-[#EEDDF2] text-[#7A3F6B]", **D},
                  tool_icon("journal"), "Farm Journal"),
            ),
            accent="#52B788",
        ),
    )
