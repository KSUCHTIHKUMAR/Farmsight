"""Port of src/hub/Journal.tsx."""
import math

from python.h import h
from python.hub.store import storage_available, uid
from python.hub.ui import H, act, all_crops, card, chip, crop_thumb, display, field, get_crop, input_cls, note, pill, style, w

from python.hub.planner import fmt_date, today_iso

TYPES = [
    {"id": "observation", "label": "Observation"},
    {"id": "scan", "label": "Scan result"},
    {"id": "watering", "label": "Watering"},
    {"id": "fertilizer", "label": "Fertilizer"},
    {"id": "harvest", "label": "Harvest"},
    {"id": "note", "label": "Note"},
]


def demo():
    d = today_iso()
    return [
        {"date": d, "type": "observation", "crop": "tomato", "title": "Lower leaves yellowing", "notes": "Demonstration entry. Spots on 3 plants near the fence.", "source": "demo"},
        {"date": d, "type": "watering", "crop": "tomato", "title": "Drip irrigation, morning", "notes": "Demonstration entry.", "source": "demo"},
        {"date": d, "type": "harvest", "crop": "maize", "title": "First cobs picked", "notes": "Demonstration entry.", "quantity": 3.5, "unit": "kg", "source": "demo"},
    ]


def label(t):
    return next((x["label"] for x in TYPES if x["id"] == t), t)


def _n(v):
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


class JournalState:
    """useState bundle; entries is the useStored value (list of entry dicts, newest first)."""

    def __init__(self, entries):
        self.entries = entries
        self.filter = "all"
        self.q = ""
        self.f = {"date": today_iso(), "type": "observation", "crop": "tomato", "title": "", "notes": "", "quantity": "", "unit": "kg"}

    def add(self):
        f = self.f
        if not f["title"].strip():
            return
        qty = None if f["quantity"].strip() == "" else float(f["quantity"])
        if qty is not None and (not math.isfinite(qty) or qty < 0):
            return
        harvest = f["type"] == "harvest"
        self.entries.insert(0, {"id": uid(), "date": f["date"], "type": f["type"], "crop": f["crop"], "title": f["title"].strip(),
                                "notes": f["notes"].strip(), "quantity": qty if harvest else None,
                                "unit": f["unit"] if harvest else None, "source": "manual"})
        f.update(title="", notes="", quantity="")

    def load_demo(self):
        self.entries[:] = [{**d, "id": uid()} for d in demo()]

    def toggle_confirmed(self, id):
        for x in self.entries:
            if x["id"] == id:
                x["confirmed"] = not x.get("confirmed")

    def delete(self, id):
        self.entries[:] = [x for x in self.entries if x["id"] != id]


def _opt(value, text, selected):
    return h("option", {"value": value, "selected": selected or None}, text)


def journal(state):
    entries = [w(e) for e in state.entries]
    f = state.f
    q = state.q
    shown = [
        e for e in entries
        if (state.filter == "all" or e.type == state.filter)
        and (not q.strip() or q.strip().lower() in f"{e.title} {e.notes} {e.crop}".lower())
    ]
    shown.sort(key=lambda e: e.date, reverse=True)

    totals = {}
    for e in entries:
        if e.type == "harvest" and e.quantity is not None:
            k = f"{e.crop}|{e.unit}"
            totals[k] = totals.get(k, 0) + (e.quantity or 0)

    crops = all_crops()
    harvest_fields = None
    if f["type"] == "harvest":
        harvest_fields = h(
            "div", {"class_": "grid grid-cols-2 gap-3"},
            field("Quantity", h("input", {**act("f-quantity"), "class_": input_cls, "inputmode": "decimal", "value": f["quantity"]})),
            field("Unit", h("select", {**act("f-unit"), "class_": input_cls, "value": f["unit"]},
                            [h("option", {"selected": f["unit"] == u or None}, u) for u in ("kg", "quintal", "tonne", "crates", "pieces")])),
        )

    new_entry = card(
        H("New entry"),
        h("div", {"class_": "grid grid-cols-1 sm:grid-cols-3 gap-3"},
          field("Date", h("input", {**act("f-date"), "type": "date", "class_": input_cls, "value": f["date"]})),
          field("Type", h("select", {**act("f-type"), "class_": input_cls, "value": f["type"]},
                          [_opt(t["id"], t["label"], f["type"] == t["id"]) for t in TYPES if t["id"] != "scan"])),
          field("Crop", h("select", {**act("f-crop"), "class_": input_cls, "value": f["crop"]},
                          [_opt(c.id, c.name, f["crop"] == c.id) for c in crops]))),
        field("Title", h("input", {**act("f-title"), "class_": input_cls, "value": f["title"], "maxlength": 80, "placeholder": "What happened?"})),
        harvest_fields,
        field("Notes", h("textarea", {**act("f-notes"), "class_": input_cls, "rows": 3, "maxlength": 500}, f["notes"])),
        h("div", {"class_": "flex flex-wrap gap-3"},
          h("button", {**act("save-entry"), "disabled": not f["title"].strip() or None,
                       "class_": "tap bg-[#2D6A4F] text-white font-bold text-sm px-5 py-3 rounded-xl disabled:opacity-40", "style": style(display)}, "Save entry"),
          h("button", {**act("load-demo"), "class_": "tap text-sm font-bold text-[#2D6A4F] bg-[#D8EFDF] px-4 py-3 rounded-xl", "style": style(display)},
            "Load demonstration entries") if not entries else None),
        class_name="space-y-3",
    )

    totals_card = None
    if totals:
        pills = []
        for k, v in totals.items():
            c, u = k.split("|")[0], k.split("|")[1]
            gc = get_crop(c)
            pills.append(pill(f"{gc.name if gc else c}: {_n(v)} {u}"))
        totals_card = card(H("Harvest totals"), h("div", {"class_": "flex flex-wrap gap-2"}, pills))

    if not shown:
        listing = card(h("p", {"class_": "text-sm text-[#5A6A59]"},
                         "No entries yet. Add one above, or save a scan result from the Results screen." if not entries else "No entries match."))
    else:
        items = []
        for e in shown:
            gc = get_crop(e.crop)
            ai = None
            if e.aiSuggestion:
                ai = pill("Confirmed by you") if e.confirmed else pill("AI suggestion, unconfirmed", color="#8A4A1C", bg="#FDE8D8")
            items.append(
                h(
                    "li",
                    {"class_": "bg-white border border-[#DDD8CE] rounded-2xl p-4 flex gap-3",
                     "style": style({"borderLeft": f"4px solid {gc.tint if gc else '#52B788'}"})},
                    crop_thumb(e.crop, gc.tint, 48) if gc else None,
                    h(
                        "div",
                        {"class_": "min-w-0 flex-1"},
                        h("div", {"class_": "flex flex-wrap items-center gap-2 mb-1"},
                          pill(label(e.type)),
                          h("span", {"class_": "text-xs text-[#5A6A59]"}, f"{fmt_date(e.date)} · {gc.name if gc else e.crop}"),
                          pill("Demonstration", color="#8A4A1C", bg="#FDE8D8") if e.source == "demo" else None,
                          ai),
                        h("p", {"class_": "text-sm font-bold text-[#1A201A]", "style": style(display)}, e.title),
                        h("p", {"class_": "text-sm text-[#3A4A38]"}, f"{_n(e.quantity)} {e.unit}") if e.quantity is not None else None,
                        h("p", {"class_": "text-sm text-[#3A4A38] mt-1"}, e.notes) if e.notes else None,
                        h("div", {"class_": "flex gap-4 mt-2"},
                          h("button", {**act("toggle-confirmed", id=e.id), "class_": "text-xs font-semibold text-[#2D6A4F]"},
                            "Mark as unconfirmed" if e.confirmed else "I have confirmed this") if e.aiSuggestion else None,
                          h("button", {**act("delete-entry", id=e.id), "class_": "text-xs font-semibold text-[#C83232]"}, "Delete")),
                    ),
                )
            )
        listing = h("ul", {"class_": "space-y-2", "aria_live": "polite"}, items)

    return h(
        "div",
        {"class_": "space-y-4"},
        note("Entries are stored in this browser only (local storage). They are not uploaded, synced or backed up, and clearing site data will erase them."
             if storage_available else "Local storage is unavailable here, so entries last only for this session and disappear on reload.",
             tone="info" if storage_available else "warn"),
        new_entry,
        totals_card,
        h(
            "div",
            {"class_": "space-y-3"},
            h("input", {**act("search"), "type": "search", "aria_label": "Search journal", "class_": input_cls, "placeholder": "Search entries", "value": q}),
            h("div", {"class_": "flex gap-2 overflow-x-auto pb-1 -mx-1 px-1", "role": "group", "aria_label": "Filter entries"},
              chip(state.filter == "all", "All", action="set-filter", filter="all"),
              [chip(state.filter == t["id"], t["label"], action="set-filter", filter=t["id"]) for t in TYPES]),
            listing,
        ),
    )
