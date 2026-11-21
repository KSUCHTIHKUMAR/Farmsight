"""Crop calendar planner (port of src/hub/planner.ts)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .crops import Crop, Priority, TaskKind

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class PlanTask:
    key: str
    title: str
    detail: str
    due: str
    priority: Priority
    kind: TaskKind
    stage: Optional[str] = None


@dataclass
class CustomTask:
    id: str
    title: str
    due: str
    priority: Priority


@dataclass
class Plan:
    id: str
    crop_id: str
    planting: str
    done: dict[str, bool] = field(default_factory=dict)
    moved: dict[str, str] = field(default_factory=dict)
    custom: list[CustomTask] = field(default_factory=list)
    custom_done: dict[str, bool] = field(default_factory=dict)


def _js_round(x: float) -> int:
    return math.floor(x + 0.5)


def _parse(iso: str) -> date:
    y, m, d = (int(p) for p in iso.split("-"))
    return date(y, m, 1) + timedelta(days=d - 1)


def today_iso() -> str:
    d = datetime.now()
    return f"{d.year}-{str(d.month).zfill(2)}-{str(d.day).zfill(2)}"


def add_days(iso: str, days: float) -> str:
    return (_parse(iso) + timedelta(days=_js_round(days))).isoformat()


def fmt_date(iso: str) -> str:
    d = _parse(iso)
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def days_between(a: str, b: str) -> int:
    return (_parse(b) - _parse(a)).days


def series(frm: float, to: float, every: float, max_count: int = 12) -> list[int]:
    span = max(to - frm, 0)
    step = max(every, math.ceil(span / max_count) or every)
    days: list[int] = []
    d = frm
    while d < to:
        days.append(d)
        d += step
    return days


def stage_at(crop: Crop, day: float) -> Optional[str]:
    for s in crop["stages"]:
        if day >= s["from"] and day < s["to"]:
            return s["name"]
    return None


def build_tasks(crop: Crop, planting: str) -> list[PlanTask]:
    p = crop["plan"]
    out: list[PlanTask] = []

    def add(key: str, title: str, detail: str, day: float, priority: Priority, kind: TaskKind) -> None:
        out.append(PlanTask(key, title, detail, add_days(planting, day), priority, kind, stage_at(crop, max(day, 0))))

    nursery = p.get("nursery")
    field_start = nursery["transplant_day"] if nursery else 0
    add("soil-test", "Consider a soil test and prepare the plot", "A soil test guides liming and fertilizer decisions. Ask your local extension service how to sample.", -14, "high", "nutrient")
    add("sow", p["start"], "Day one of the nursery. Use healthy, clean seed or planting material." if nursery else "Use healthy, clean planting material suited to your region.", 0, "high", "sow")
    if nursery:
        add("harden", "Harden off seedlings", "Gradually expose seedlings to field conditions before transplanting.", nursery["transplant_day"] - 5, "medium", "transplant")
        add("transplant", "Transplant seedlings to the field", "Transplant when seedlings are sturdy; water in well.", nursery["transplant_day"], "high", "transplant")
    for i, d in enumerate(series(field_start, p["horizon"], p["irrig_every"])):
        add(f"irr-{i}", "Irrigation check", "Check soil moisture at root depth and water as the crop and weather require.", d + 2, "medium", "irrigation")
    for i, d in enumerate(series(field_start + 7, min(p["horizon"], p["harvest_from"] * 0.7 if p["harvest_from"] < 9999 else p["horizon"]), p["weed_every"])):
        add(f"weed-{i}", "Weeding", "Remove weeds that compete for light, water and nutrients or harbour pests.", d, "low", "weeding")
    for i, d in enumerate(series(field_start + 10, p["horizon"], p["nutrient_every"])):
        add(f"nut-{i}", "Nutrient monitoring", "Check leaf colour and growth against soil test results. Adjust only on local advice.", d, "medium", "nutrient")
    for i, d in enumerate(series(field_start + 5, p["horizon"], p["scout_every"])):
        add(f"scout-{i}", "Disease and pest scouting", "Inspect leaves, stems and fruit. AI scan results are only suggestions until confirmed.", d, "high", "scouting")
    for t in p.get("extra") or []:
        add(t["key"], t["title"], t["detail"], t["day"], t["priority"], t["kind"])
    if p["harvest_from"] < 9999:
        add("harvest-prep", "Prepare for harvest", "Clean tools and containers, and review the maturity indicators for this crop.", p["harvest_from"] - 7, "medium", "harvest")
        add("harvest", "Begin harvest checks", crop["harvest"][0], p["harvest_from"], "high", "harvest")
    return sorted(out, key=lambda t: t.due)


@dataclass
class FlatTask:
    plan_id: str
    crop_id: str
    key: str
    custom: bool
    title: str
    detail: str
    due: str
    priority: Priority
    kind: TaskKind
    done: bool


def flatten_plan(plan: Plan, crop: Crop) -> list[FlatTask]:
    generated = [
        FlatTask(plan.id, plan.crop_id, t.key, False, t.title, t.detail, plan.moved.get(t.key, t.due),
                 t.priority, t.kind, bool(plan.done.get(t.key)))
        for t in build_tasks(crop, plan.planting)
    ]
    custom = [
        FlatTask(plan.id, plan.crop_id, c.id, True, c.title, "Your own task.", c.due, c.priority, "other",
                 bool(plan.custom_done.get(c.id)))
        for c in plan.custom
    ]
    return sorted(generated + custom, key=lambda t: t.due)
