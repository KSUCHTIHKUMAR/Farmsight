"""Port of src/hub/CalendarView.tsx."""
from python.h import h
from python.hub.crops import ABOUT_TIMINGS
from python.hub.store import PLANS_KEY, storage_available, uid  # noqa: F401
from python.hub.ui import (H, act, all_crops, card, chip, crop_thumb, display, field, get_crop, input_cls, note, pill, style, w)

from python.hub.planner import CustomTask, Plan, add_days, days_between, flatten_plan, fmt_date, today_iso


def as_plan(p):
    """Persisted plans are snake_case dicts (JSON); planner expects Plan dataclasses."""
    if isinstance(p, Plan):
        return p
    return Plan(p["id"], p["crop_id"], p["planting"], p.get("done", {}), p.get("moved", {}),
                [c if isinstance(c, CustomTask) else CustomTask(**c) for c in p.get("custom", [])], p.get("custom_done", {}))

PRI = {
    "high": {"label": "High", "color": "#C83232", "bg": "#FCE4E4"},
    "medium": {"label": "Medium", "color": "#8A4A1C", "bg": "#FDE8D8"},
    "low": {"label": "Low", "color": "#2D6A4F", "bg": "#D8EFDF"},
}

_PRIMARY = "tap bg-[#2D6A4F] text-white font-bold text-sm px-5 py-3 rounded-xl"


class CalendarState:
    """useState bundle. plans is the useStored value (list of plan dicts; mutate then persist)."""

    def __init__(self, plans, initial_crop=None):
        self.plans = plans
        self.crop_id = initial_crop or "tomato"
        self.date = today_iso()
        self.active_id = plans[0]["id"] if plans else None
        self.status = "all"
        self.prio = "all"
        self.nt = {"title": "", "due": today_iso(), "priority": "medium"}

    # ---- handlers (data-action ids: create-plan, patch via toggle/move/add-custom/remove-plan) ----
    def active_plan(self):
        return next((p for p in self.plans if p["id"] == self.active_id), None)

    def create_plan(self):
        if not self.date:
            return
        p = {"id": uid(), "crop_id": self.crop_id, "planting": self.date, "done": {}, "moved": {}, "custom": [], "custom_done": {}}
        self.plans.append(p)
        self.active_id = p["id"]

    def toggle(self, t):
        p = self.active_plan()
        if p is None:
            return
        if t.custom:
            p["custom_done"][t.key] = not t.done
        else:
            p["done"][t.key] = not t.done

    def move(self, t, due):
        p = self.active_plan()
        if not due or p is None:
            return
        if t.custom:
            for c in p["custom"]:
                if c["id"] == t.key:
                    c["due"] = due
        else:
            p["moved"][t.key] = due

    def add_custom(self):
        nt = self.nt
        p = self.active_plan()
        if not nt["title"].strip() or not nt["due"] or p is None:
            return
        p["custom"].append({"id": uid(), "title": nt["title"].strip(), "due": nt["due"], "priority": nt["priority"]})
        nt["title"] = ""

    def remove_plan(self):
        self.plans[:] = [p for p in self.plans if p["id"] != self.active_id]
        self.active_id = None


def _pct(v):
    s = repr(float(v))
    return s[:-2] if s.endswith(".0") else s


def _opt(value, label, selected):
    return h("option", {"value": value, "selected": selected or None}, label)


def calendar_view(state):
    plans = state.plans
    plan_raw = state.active_plan()
    plan = w(plan_raw) if plan_raw else None
    crop = get_crop(plan.crop_id) if plan else None
    today = today_iso()
    crops = all_crops()

    tasks = [w(t) for t in flatten_plan(as_plan(plan_raw), crop._raw)] if plan and crop else []

    def keep(t):
        overdue = not t.done and t.due < today
        if state.status == "pending" and t.done:
            return False
        if state.status == "done" and not t.done:
            return False
        if state.status == "overdue" and not overdue:
            return False
        return state.prio == "all" or t.priority == state.prio

    shown = [t for t in tasks if keep(t)]
    done_count = len([t for t in tasks if t.done])
    nt = state.nt
    sel_crop = get_crop(state.crop_id)

    new_plan = card(
        H("New plan"),
        h(
            "div",
            {"class_": "grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-3 items-end"},
            field("Crop", h("select", {**act("set-crop"), "class_": input_cls, "value": state.crop_id},
                            [_opt(c.id, c.name, c.id == state.crop_id) for c in crops])),
            field((sel_crop.plan.start if sel_crop else None) or "Planting date",
                  h("input", {**act("set-date"), "type": "date", "class_": input_cls, "value": state.date})),
            h("button", {**act("create-plan"), "disabled": not state.date or None,
                         "class_": _PRIMARY + " hover:bg-[#235a41] disabled:opacity-40", "style": style(display)}, "Create plan"),
        ),
        h("p", {"class_": "text-xs text-[#5A6A59]"},
          "Plans are saved in this browser only (local storage). They are not synced or backed up." if storage_available
          else "Local storage is unavailable here, so plans last only until you close or reload this page."),
        class_name="space-y-3",
    )

    plan_chips = None
    if plans:
        plan_chips = h(
            "div",
            {"class_": "flex gap-2 overflow-x-auto pb-1 -mx-1 px-1", "role": "group", "aria_label": "Your plans"},
            [chip(p["id"] == state.active_id,
                  f"{(get_crop(p['crop_id']).name if get_crop(p['crop_id']) else '')} · {fmt_date(p['planting'])}",
                  action="select-plan", plan_id=p["id"]) for p in plans],
        )

    if plan and crop:
        now_day = days_between(plan.planting, today)
        stage_items = []
        for s in crop.stages:
            fr = getattr(s, "from")
            frm = fmt_date(add_days(plan.planting, fr))
            to = fmt_date(add_days(plan.planting, s.to))
            current = fr <= now_day < s.to
            stage_items.append(
                h(
                    "li",
                    {"class_": "rounded-xl px-3 py-2 border text-sm " + ("border-[#52B788] bg-[#F3FAF5]" if current else "border-[#EEEAE1]")},
                    h("div", {"class_": "flex flex-wrap justify-between gap-1"},
                      h("span", {"class_": "font-bold text-[#1A201A]", "style": style(display)}, s.name,
                        h("span", {"class_": "ml-2 text-xs font-semibold text-[#2D6A4F]"}, "current estimate") if current else None),
                      h("span", {"class_": "text-xs text-[#5A6A59]"}, f"about {frm} to {to}")),
                    h("p", {"class_": "text-xs text-[#5A6A59]"}, s.note),
                )
            )

        task_items = []
        for t in shown:
            overdue = not t.done and t.due < today
            box = "bg-[#F5F2EC] border-[#EEEAE1]" if t.done else ("border-[#F2B8B8] bg-[#FFF7F7]" if overdue else "border-[#DDD8CE]")
            pri = PRI[t.priority]
            task_items.append(
                h(
                    "li",
                    {"class_": f"rounded-xl border p-3 flex gap-3 {box}"},
                    h("input", {**act("toggle-task", key=t.key), "type": "checkbox", "checked": bool(t.done),
                                "aria_label": f"Mark {t.title} done", "class_": "mt-1 w-5 h-5 accent-[#2D6A4F] flex-shrink-0"}),
                    h(
                        "div",
                        {"class_": "min-w-0 flex-1"},
                        h("p", {"class_": "text-sm font-semibold " + ("line-through text-[#5A6A59]" if t.done else "text-[#1A201A]"), "style": style(display)}, t.title),
                        h("p", {"class_": "text-xs text-[#5A6A59] mt-0.5"}, t.detail),
                        h("div", {"class_": "flex flex-wrap items-center gap-2 mt-2"},
                          pill(pri["label"], color=pri["color"], bg=pri["bg"]),
                          pill("Overdue", color="#C83232", bg="#FCE4E4") if overdue else None,
                          h("label", {"class_": "flex items-center gap-1 text-xs text-[#5A6A59]"}, "Due",
                            h("input", {**act("move-task", key=t.key), "type": "date", "value": t.due,
                                        "class_": "rounded-lg border border-[#DDD8CE] px-2 py-1 text-xs text-[#1A201A]"}))),
                    ),
                )
            )

        task_list = (
            h("p", {"class_": "text-sm text-[#5A6A59]"}, "No tasks match these filters.") if not shown
            else h("ul", {"class_": "space-y-2", "aria_live": "polite"}, task_items)
        )
        width = _pct(done_count / len(tasks) * 100) if tasks else "0"

        body = h(
            "div",
            {"class_": "space-y-4 animate-fade-in"},
            card(
                h("div", {"class_": "flex items-center gap-3 mb-4 rounded-xl p-2", "style": style({"backgroundColor": crop.tintBg})},
                  crop_thumb(crop.id, crop.tint, 52),
                  h("div", None,
                    h("p", {"class_": "font-extrabold", "style": style(display, {"color": crop.tint})}, crop.name),
                    h("p", {"class_": "text-xs text-[#3A4A38]"}, f"{crop.plan.start}: {fmt_date(plan.planting)}"))),
                h("div", {"class_": "flex flex-wrap items-center justify-between gap-2 mb-3"},
                  H("Estimated growth stages"),
                  h("button", {**act("remove-plan"), "class_": "text-xs font-semibold text-[#C83232]"}, "Delete plan")),
                h("ol", {"class_": "space-y-2"}, stage_items),
                h("p", {"class_": "text-xs text-[#5A6A59] mt-3"}, crop.plan.harvestNote) if crop.plan.harvestNote else None,
                accent=crop.tint,
            ),
            card(
                h("div", {"class_": "flex items-center justify-between mb-3 gap-2"},
                  H("Tasks"), pill(f"{done_count} of {len(tasks)} done")),
                h("div", {"class_": "h-2 rounded-full bg-[#E8E4DB] overflow-hidden mb-3", "aria_hidden": "true"},
                  h("div", {"class_": "h-full bg-[#52B788] transition-all duration-300", "style": style({"width": f"{width}%"})})),
                h("div", {"class_": "flex flex-wrap gap-2 mb-2", "role": "group", "aria_label": "Filter by status"},
                  [chip(state.status == s, s[0].upper() + s[1:], action="set-status", status=s) for s in ("all", "pending", "overdue", "done")]),
                h("div", {"class_": "flex flex-wrap gap-2 mb-4", "role": "group", "aria_label": "Filter by priority"},
                  [chip(state.prio == s, "Any priority" if s == "all" else PRI[s]["label"], action="set-prio", prio=s) for s in ("all", "high", "medium", "low")]),
                task_list,
                accent="#2B6A8F",
            ),
            card(
                H("Add your own task"),
                h("div", {"class_": "grid grid-cols-1 sm:grid-cols-[1fr_auto_auto_auto] gap-3 items-end"},
                  field("Task", h("input", {**act("nt-title"), "class_": input_cls, "value": nt["title"], "maxlength": 80, "placeholder": "e.g. Repair drip line"})),
                  field("Due", h("input", {**act("nt-due"), "type": "date", "class_": input_cls, "value": nt["due"]})),
                  field("Priority", h("select", {**act("nt-priority"), "class_": input_cls, "value": nt["priority"]},
                                      _opt("high", "High", nt["priority"] == "high"),
                                      _opt("medium", "Medium", nt["priority"] == "medium"),
                                      _opt("low", "Low", nt["priority"] == "low"))),
                  h("button", {**act("add-custom"), "disabled": not nt["title"].strip() or None,
                               "class_": _PRIMARY + " disabled:opacity-40", "style": style(display)}, "Add")),
            ),
        )
    else:
        body = card(h("p", {"class_": "text-sm text-[#5A6A59]"}, "No plan selected. Create one above to see stages and tasks."))

    return h(
        "div",
        {"class_": "space-y-4"},
        note(f"{ABOUT_TIMINGS} Treat every date here as a suggestion to adjust to your own field.", tone="warn"),
        new_plan,
        plan_chips,
        body,
    )
