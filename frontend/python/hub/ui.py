"""Port of src/hub/ui.tsx. Components return HTML strings via python.h.h."""
import re

from python.h import h
from python.hub.crops import crop_img

TOOLS = [
    {"id": "overview", "label": "Farm Overview", "subtitle": "Tasks and shortcuts"},
    {"id": "hub", "label": "Knowledge Hub", "subtitle": "Crop profiles and search"},
    {"id": "care", "label": "Crop Care Guide", "subtitle": "Soil, nutrients, prevention"},
    {"id": "calendar", "label": "Crop Calendar", "subtitle": "Stages and tasks"},
    {"id": "journal", "label": "Farm Journal", "subtitle": "Records and scan notes"},
]

display = {"fontFamily": "Manrope, sans-serif"}

input_cls = (
    "w-full rounded-xl border border-[#DDD8CE] bg-white px-3 py-2.5 text-sm text-[#1A201A] "
    "focus:outline-none focus:ring-2 focus:ring-[#52B788]"
)

_PX = {"width", "height", "fontSize"}


def _num(n):
    return f"{round(n, 4):g}" if isinstance(n, float) else str(n)


def style(*dicts):
    """React-style dict(s) (camelCase keys) -> inline CSS string. Falsy dicts skipped."""
    out = []
    for d in dicts:
        for k, v in (d or {}).items():
            kebab = re.sub(r"([A-Z])", lambda m: "-" + m.group(1).lower(), k)
            if isinstance(v, (int, float)) and k in _PX:
                v = _num(v) + "px"
            out.append(f"{kebab}: {v}")
    return "; ".join(out) or None


def act(action, **params):
    """Event handler -> data-action attrs (data_x -> data-x)."""
    d = {"data_action": action}
    for k, v in params.items():
        if v is not None:
            d["data_" + k] = v
    return d


class Obj:
    """Attribute proxy over dict/object data; accepts camelCase or snake_case names."""

    def __init__(self, raw):
        object.__setattr__(self, "_raw", raw)

    def __getattr__(self, name):
        raw = self._raw
        snake = re.sub(r"([A-Z])", lambda m: "_" + m.group(1).lower(), name)
        for n in (name, snake):
            if isinstance(raw, dict):
                if n in raw:
                    return w(raw[n])
            elif hasattr(raw, n):
                return w(getattr(raw, n))
        return None

    def __getitem__(self, k):
        return w(self._raw[k])


def w(v):
    if isinstance(v, (list, tuple)):
        return [w(x) for x in v]
    if v is None or isinstance(v, (str, int, float, bool, Obj)):
        return v
    return Obj(v)


def card(*children, class_name="", accent=None):
    return h(
        "div",
        {
            "class_": f"bg-white border border-[#DDD8CE] rounded-2xl p-4 sm:p-5 {class_name}",
            "style": style({"borderTop": f"3px solid {accent}"}) if accent else None,
        },
        *children,
    )


def crop_thumb(id, tint, size=44):
    return h(
        "img",
        {
            "src": crop_img(id, size * 3, size * 3),
            "alt": "",
            "loading": "lazy",
            "class_": "rounded-2xl object-cover flex-shrink-0",
            "style": style({"width": size, "height": size, "boxShadow": f"0 0 0 2px #fff, 0 0 0 4px {tint}55"}),
        },
    )


TOOL_LOOK = {
    "overview": {"from": "#2D6A4F", "image": "vineyard"},
    "hub": {"from": "#2D6A4F", "image": "vineyard"},
    "care": {"from": "#8A5A22", "image": "potato"},
    "calendar": {"from": "#2B6A8F", "image": "watermelon"},
    "journal": {"from": "#7A3F6B", "image": "grapes"},
}


def tool_banner(tool, title, subtitle):
    look = TOOL_LOOK[tool]
    f = look["from"]
    return h(
        "div",
        {"class_": "relative rounded-2xl overflow-hidden mb-4 min-h-[7rem] sm:min-h-[9rem] flex items-end"},
        h("img", {"src": crop_img(look["image"], 1000, 400), "alt": "", "class_": "absolute inset-0 w-full h-full object-cover"}),
        h("div", {"class_": "absolute inset-0", "style": style({"background": f"linear-gradient(100deg, {f}F2 0%, {f}B3 55%, {f}26 100%)"})}),
        h(
            "div",
            {"class_": "relative p-4 sm:p-6 text-white max-w-md"},
            h("h2", {"class_": "text-xl sm:text-2xl font-extrabold", "style": style(display)}, title),
            h("p", {"class_": "text-xs sm:text-sm text-white/85 mt-1"}, subtitle),
        ),
    )


def H(*children):
    return h("h3", {"class_": "text-base sm:text-lg font-extrabold text-[#1A201A] mb-3", "style": style(display)}, *children)


def note(*children, tone="info"):
    cls = "bg-[#FDE8D8] text-[#8A4A1C]" if tone == "warn" else "bg-[#D8EFDF] text-[#1F4F3A]"
    return h("p", {"class_": f"{cls} rounded-xl px-4 py-3 text-xs leading-relaxed font-medium"}, *children)


def pill(*children, color="#2D6A4F", bg="#D8EFDF"):
    return h(
        "span",
        {
            "class_": "inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full whitespace-nowrap",
            "style": style({"color": color, "backgroundColor": bg}),
        },
        *children,
    )


def field(label, *children):
    return h(
        "label",
        {"class_": "block"},
        h("span", {"class_": "block text-xs font-semibold text-[#3A4A38] mb-1"}, label),
        *children,
    )


def chip(on, *children, action=None, **params):
    """action/params become data-action / data-* attributes (the onClick handler)."""
    return h(
        "button",
        {
            **(act(action, **params) if action else {}),
            "aria_pressed": "true" if on else "false",
            "class_": "tap whitespace-nowrap text-sm font-semibold px-4 py-2 rounded-full border transition-colors duration-150 "
            + ("bg-[#2D6A4F] text-white border-[#2D6A4F]" if on else "bg-white text-[#3A4A38] border-[#DDD8CE] hover:border-[#52B788]"),
            "style": style(display),
        },
        *children,
    )


def bullets(items):
    return h(
        "ul",
        {"class_": "list-disc pl-5 text-sm text-[#3A4A38] space-y-1.5 leading-relaxed"},
        [h("li", None, i) for i in items],
    )


def monogram(name, tint, bg, size=44):
    return h(
        "div",
        {
            "class_": "rounded-2xl flex items-center justify-center font-extrabold flex-shrink-0",
            "style": style({"width": size, "height": size, "color": tint, "backgroundColor": bg, "fontSize": size * 0.42}, display),
        },
        name[0],
    )


def tool_icon(id, color="currentColor", size=16):
    p = {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none", "stroke": color,
         "stroke_width": 2, "stroke_linecap": "round", "stroke_linejoin": "round"}
    if id == "hub":
        return h("svg", p, h("path", {"d": "M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2z"}), h("path", {"d": "M8 7h6M8 11h6"}))
    if id == "care":
        return h("svg", p, h("path", {"d": "M12 22V10"}), h("path", {"d": "M12 14c0-4-3-6-7-6 0 4 3 6 7 6zM12 12c0-4 3-6 7-6 0 4-3 6-7 6z"}))
    if id == "calendar":
        return h("svg", p, h("rect", {"x": 3, "y": 5, "width": 18, "height": 16, "rx": 2}), h("path", {"d": "M3 10h18M8 3v4M16 3v4"}))
    if id == "journal":
        return h("svg", p, h("path", {"d": "M5 3h12a2 2 0 0 1 2 2v16H7a2 2 0 0 1-2-2z"}), h("path", {"d": "M9 8h6M9 12h6"}))
    return h("svg", p, h("path", {"d": "M3 12l9-8 9 8"}), h("path", {"d": "M5 10v10h14V10"}))


def all_crops():
    from python.hub import crops as _c
    return w(_c.CROPS)


def get_crop(id):
    from python.hub import crops as _c
    return w(_c.get_crop(id))
