"""Port of src/scan/ScanViews.tsx. Components are functions returning HTML strings.

Handlers are expressed as data-action attributes; state lives in small classes.
"""
import math
import re

from python.h import h
from python.hub.scan_follow_up import ScanFollowUpState, scan_follow_up
from python.lib.api import AnalyseError, fmt_pct, is_healthy_name, pct
from python.lib.i18n import use_t

display = "font-family: Manrope, sans-serif"
MUTED = "#5A6A59"

TONES = {
    "good": {"fg": "#1F5A41", "bg": "#D8EFDF", "bar": "#2D6A4F"},
    "bad": {"fg": "#A81F1F", "bg": "#FCE4E4", "bar": "#C83232"},
    "warn": {"fg": "#8A4B00", "bg": "#FFEFD2", "bar": "#D9822B"},
    "unsure": {"fg": "#8A4B00", "bg": "#FFEFD2", "bar": "#D9822B"},
}


def _g(o, k, default=None):
    """Read a field from a dict or an object."""
    if o is None:
        return default
    if isinstance(o, dict):
        return o.get(k, default)
    return getattr(o, k, default)


def _get_t():
    r = use_t()
    if callable(r):
        return r
    if isinstance(r, dict):
        return r["t"]
    return r.t


# -- State classes -------------------------------------------------------------


class CameraState:
    def __init__(self, status="starting"):
        self.status = status  # 'starting' | 'live' | 'unavailable'


class InputState:
    def __init__(self):
        self.camera_open = False
        self.camera = CameraState()


class LoadingState:
    def __init__(self):
        self.slow = False  # set True after 6000 ms


class RingState:
    def __init__(self):
        self.on = False  # set True after 120 ms


class SliderState:
    def __init__(self, pos=50):
        self.pos = pos


# -- Small icons ---------------------------------------------------------------


def Svg(children, size=20, color="currentColor"):
    return h(
        "svg",
        {
            "width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none",
            "stroke": color, "stroke_width": "2", "stroke_linecap": "round",
            "stroke_linejoin": "round", "aria_hidden": "true", "class_": "flex-shrink-0",
        },
        *children,
    )


def CameraI(size=20, color="currentColor"):
    return Svg([
        h("path", {"d": "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"}),
        h("circle", {"cx": "12", "cy": "13", "r": "4"}),
    ], size, color)


def UploadI(size=20, color="currentColor"):
    return Svg([h("path", {"d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"})], size, color)


def CheckI(size=20, color="currentColor"):
    return Svg([
        h("circle", {"cx": "12", "cy": "12", "r": "10"}),
        h("path", {"d": "M8 12l3 3 5-6"}),
    ], size, color)


def AlertI(size=20, color="currentColor"):
    return Svg([h("path", {"d": "M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01"})], size, color)


def RetryI(size=20, color="currentColor"):
    return Svg([h("path", {"d": "M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15"})], size, color)


def LeafI(size=20, color="currentColor"):
    return Svg([h("path", {"d": "M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10zM2 21c0-3 1.9-5.5 6-7"})], size, color)


primaryBtn = "w-full flex items-center justify-center gap-2.5 bg-[#2D6A4F] text-white font-bold text-base min-h-14 py-3.5 rounded-2xl hover:bg-[#235a41] tap"
secondaryBtn = "w-full flex items-center justify-center gap-2.5 bg-white border-2 border-[#2D6A4F] text-[#2D6A4F] font-bold text-base min-h-14 py-3.5 rounded-2xl hover:bg-[#F5F2EC] tap"

# -- Camera --------------------------------------------------------------------


def CameraCapture(task, camera=None):
    """Handlers: scan:upload-fallback, scan:close-camera, scan:shoot."""
    t = _get_t()
    camera = camera or CameraState()
    status = camera.status
    tips = [t("camTipLeaf") if task == "leaf" else t("camTipPest") if task == "pest" else t("camTipFruit"), t("camTipLight")]
    corner = "absolute w-7 h-7 border-white"

    live = []
    if status == "live":
        live = [
            h("div", {"class_": "absolute inset-[12%] rounded-3xl pointer-events-none", "style": "box-shadow: 0 0 0 999px rgba(10,16,10,0.5)", "aria_hidden": "true"},
              h("span", {"class_": f"{corner} top-0 left-0 border-t-4 border-l-4 rounded-tl-3xl"}),
              h("span", {"class_": f"{corner} top-0 right-0 border-t-4 border-r-4 rounded-tr-3xl"}),
              h("span", {"class_": f"{corner} bottom-0 left-0 border-b-4 border-l-4 rounded-bl-3xl"}),
              h("span", {"class_": f"{corner} bottom-0 right-0 border-b-4 border-r-4 rounded-br-3xl"})),
            h("p", {"class_": "absolute top-3 inset-x-3 text-center text-xs font-semibold text-white bg-black/55 rounded-full py-1.5 px-3 mx-auto w-fit max-w-full"}, t("camGuide")),
            h("p", {"class_": "absolute bottom-3 inset-x-3 text-center text-sm font-bold text-white mx-auto w-fit max-w-full bg-[#2D6A4F] rounded-full py-1.5 px-4", "style": display}, tips[0]),
        ]

    return h(
        "div", {"class_": "space-y-4 animate-fade-in"},
        h("div", {"class_": "relative rounded-2xl overflow-hidden bg-[#101510] mx-auto", "style": "aspect-ratio: 3/4; max-height: 68dvh"},
          h("video", {"playsinline": True, "muted": True, "aria_label": t("takePhoto"), "data_ref": "video",
                      "class_": f"absolute inset-0 w-full h-full object-cover {'' if status == 'live' else 'invisible'}"}),
          live,
          status == "starting" and h("p", {"role": "status", "class_": "absolute inset-0 flex items-center justify-center text-sm text-white/90"}, t("camStarting")),
          status == "unavailable" and h(
              "div", {"role": "alert", "class_": "absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center"},
              CameraI(32, "#fff"),
              h("p", {"class_": "text-sm text-white leading-relaxed"}, t("camUnavailable")),
              h("button", {"data_action": "scan:upload-fallback", "class_": "bg-white text-[#1F5A41] font-bold text-sm min-h-11 px-5 rounded-xl tap", "style": display}, t("camUseUpload")))),
        h("ul", {"class_": "bg-[#D8EFDF] rounded-xl px-4 py-3 space-y-1.5"},
          [h("li", {"class_": "flex items-center gap-2 text-sm font-medium text-[#1F5A41]"}, CheckI(16, "#1F5A41"), tip) for tip in tips]),
        h("div", {"class_": "flex items-center justify-between gap-4 pt-1"},
          h("button", {"data_action": "scan:close-camera", "class_": "min-h-12 px-5 rounded-xl text-sm font-bold text-[#2D4A3A] bg-[#E8E4DB] hover:bg-[#DDD8CE] tap", "style": display}, t("cancel")),
          h("button", {"data_action": "scan:shoot", "disabled": status != "live", "aria_label": t("capture"),
                       "class_": "w-[72px] h-[72px] rounded-full bg-white border-[5px] border-[#2D6A4F] flex items-center justify-center disabled:opacity-40 tap"},
            h("span", {"class_": "w-12 h-12 rounded-full bg-[#2D6A4F]"})),
          h("span", {"class_": "w-[76px]", "aria_hidden": "true"})),
    )


# -- Input ---------------------------------------------------------------------


def InputMethodContent(task, state=None):
    """Handlers: scan:file-change (capture), scan:upload-click, scan:open-camera."""
    t = _get_t()
    state = state or InputState()
    file_input = h("input", {"data_ref": "file-input", "type": "file", "accept": "image/*", "class_": "hidden", "tabindex": -1, "data_action": "scan:file-change"})

    if state.camera_open:
        return [CameraCapture(task, state.camera), file_input]

    img = ("https://images.unsplash.com/photo-1642307321395-b72347cbe944?w=700&h=525&fit=crop&auto=format"
           if task == "leaf" else
           "https://images.unsplash.com/photo-1631739196439-5eac4cc2dc6d?w=700&h=525&fit=crop&auto=format"
           if task == "pest" else
           "https://images.unsplash.com/photo-1707734534246-b456bdb7db6c?w=700&h=525&fit=crop&auto=format")
    return h(
        "div", {"class_": "space-y-5"},
        h("div", None,
          h("h2", {"class_": "text-2xl font-extrabold text-[#1A201A] mb-1.5", "style": display}, t("addPhoto")),
          h("p", {"class_": "text-sm leading-relaxed", "style": f"color: {MUTED}"}, t("tipLeaf") if task == "leaf" else t("tipPest") if task == "pest" else t("tipProduce"))),
        h("div", {"class_": "relative rounded-2xl overflow-hidden bg-[#E8E4DB]", "style": "aspect-ratio: 4/3"},
          h("img", {"src": img, "alt": "Example of a leaf photo" if task == "leaf" else "Example of a pest photo" if task == "pest" else "Example of a fruit photo", "class_": "w-full h-full object-cover opacity-60"}),
          h("div", {"class_": "absolute inset-0 flex items-center justify-center p-4"},
            h("div", {"class_": "bg-white/90 backdrop-blur-sm rounded-2xl px-4 py-3 flex items-center gap-2.5"},
              CameraI(18, "#2D6A4F"),
              h("span", {"class_": "text-sm font-semibold text-[#1F5A41]", "style": display}, t("photoHere"))))),
        h("div", {"class_": "bg-[#D8EFDF] rounded-xl px-4 py-3 flex gap-3"},
          CheckI(16, "#1F5A41"),
          h("p", {"class_": "text-xs text-[#1F5A41] leading-relaxed font-medium"}, t("bestResults"))),
        h("div", {"class_": "space-y-3"},
          h("button", {"data_action": "scan:upload-click", "class_": primaryBtn, "style": display}, UploadI(20, "#fff"), t("upload")),
          h("button", {"data_action": "scan:open-camera", "class_": secondaryBtn, "style": display}, CameraI(20, "#2D6A4F"), t("takePhoto"))),
        file_input,
    )


# -- Loading -------------------------------------------------------------------


def LoadingContent(image, state=None):
    t = _get_t()
    state = state or LoadingState()
    slow = state.slow
    return h(
        "div", {"class_": "flex flex-col items-center justify-center py-10 text-center", "role": "status", "aria_live": "polite"},
        h("div", {"class_": "relative w-[min(300px,72vw)] aspect-square rounded-2xl overflow-hidden bg-[#1A201A] mb-7"},
          h("img", {"src": image, "alt": t("submittedPhoto"), "class_": "w-full h-full object-cover"}) if image else
          h("div", {"class_": "w-full h-full flex items-center justify-center"}, LeafI(40, "#52B788")),
          h("div", {"class_": "scan-sweep", "aria_hidden": "true"}),
          h("div", {"class_": "scan-line", "aria_hidden": "true"})),
        h("h2", {"class_": "text-xl font-bold text-[#1A201A]", "style": display}, t("analysing")),
        h("p", {"class_": f"text-sm mt-3 transition-opacity duration-300 {'opacity-100' if slow else 'opacity-0'}", "style": f"color: {MUTED}"}, t("analysingSlow")),
    )


# -- Results -------------------------------------------------------------------


def cap(s):
    return s[:1].upper() + s[1:]


def ConfidenceRing(value, tone, label, state=None):
    t = _get_t()
    state = state or RingState()
    R = 44
    C = 2 * math.pi * R
    v = min(100, max(0, value))
    return h(
        "div", {"class_": "relative w-[104px] h-[104px] flex-shrink-0", "role": "img", "aria_label": f"{t('confidence')} {label}"},
        h("svg", {"viewBox": "0 0 104 104", "class_": "w-full h-full -rotate-90", "aria_hidden": "true"},
          h("circle", {"cx": "52", "cy": "52", "r": R, "fill": "none", "stroke": "#E8E4DB", "stroke_width": "9"}),
          h("circle", {"cx": "52", "cy": "52", "r": R, "fill": "none", "stroke": TONES[tone]["bar"], "stroke_width": "9",
                       "stroke_linecap": "round", "stroke_dasharray": C,
                       "stroke_dashoffset": C * (1 - v / 100) if state.on else C,
                       "style": "transition: stroke-dashoffset 900ms cubic-bezier(.2,.8,.2,1)"})),
        h("div", {"class_": "absolute inset-0 flex flex-col items-center justify-center", "aria_hidden": "true"},
          h("span", {"class_": "text-2xl font-extrabold text-[#1A201A] leading-none", "style": display}, label),
          h("span", {"class_": "text-[11px] mt-1", "style": f"color: {MUTED}"}, t("confidence"))),
    )


def TopBars(result, tone):
    t = _get_t()
    items = (_g(result, "top") or [])[:3]
    rows = []
    for i, g in enumerate(items):
        prob = _g(g, "prob")
        rows.append(h(
            "li", None,
            h("div", {"class_": "flex items-baseline justify-between gap-3 text-sm mb-1"},
              h("span", {"class_": "font-bold text-[#1A201A]" if i == 0 else "text-[#3A4A38]"}, _g(g, "name")),
              h("span", {"class_": "font-bold tabular-nums", "style": f"{display}; color: {TONES[tone]['fg'] if i == 0 else '#3A4A38'}"}, fmt_pct(prob))),
            h("div", {"class_": "h-2.5 bg-[#E8E4DB] rounded-full overflow-hidden", "role": "meter", "aria_label": _g(g, "name"),
                      "aria_valuemin": 0, "aria_valuemax": 100, "aria_valuenow": round(pct(prob))},
              h("div", {"class_": "h-full rounded-full",
                        "style": f"width: {min(100, pct(prob))}%; background-color: {TONES[tone]['bar'] if i == 0 else '#6F8A77'}; transition: width 600ms ease-out"})),
        ))
    return h("section", {"class_": "bg-white border border-[#DDD8CE] rounded-2xl p-4"},
             h("h3", {"class_": "text-sm font-bold text-[#1A201A] mb-3", "style": display}, t("top3")),
             h("ol", {"class_": "space-y-3"}, rows))


def CompareSlider(photo, heatmap, state=None):
    """Handler: scan:compare-change (input event on the range)."""
    t = _get_t()
    state = state or SliderState()
    pos = state.pos
    return h(
        "figure", {"class_": "bg-white border border-[#DDD8CE] rounded-2xl p-3"},
        h("div", {"class_": "relative aspect-square rounded-xl overflow-hidden bg-[#1A201A] select-none"},
          h("img", {"src": photo, "alt": t("photoAlt"), "class_": "absolute inset-0 w-full h-full object-cover", "draggable": "false"}),
          h("img", {"src": heatmap, "alt": t("heatmapAlt"), "class_": "absolute inset-0 w-full h-full object-cover", "style": f"clip-path: inset(0 0 0 {pos}%)", "draggable": "false"}),
          h("input", {"type": "range", "min": 0, "max": 100, "step": 1, "value": pos, "data_action": "scan:compare-change",
                      "aria_label": t("compareHint"), "aria_valuetext": f"{t('photo')} {pos}% / {t('heatmap')} {100 - pos}%",
                      "class_": "peer absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-10",
                      "style": "touch-action: pan-y; min-height: 44px"}),
          h("div", {"class_": "absolute inset-y-0 w-0.5 bg-white pointer-events-none shadow-[0_0_6px_rgba(0,0,0,0.5)]", "style": f"left: {pos}%", "aria_hidden": "true"},
            h("span", {"class_": "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white shadow-lg flex items-center justify-center text-[#2D6A4F] font-bold text-lg"}, "⇆")),
          h("span", {"class_": "absolute top-2 left-2 text-xs font-bold text-white bg-black/65 rounded-full px-2.5 py-1 pointer-events-none"}, t("photo")),
          h("span", {"class_": "absolute top-2 right-2 text-xs font-bold text-white bg-black/65 rounded-full px-2.5 py-1 pointer-events-none"}, t("heatmap")),
          h("span", {"class_": "absolute inset-0 rounded-xl ring-4 ring-[#52B788] ring-inset opacity-0 peer-focus-visible:opacity-100 pointer-events-none", "aria_hidden": "true"})),
        h("figcaption", {"class_": "flex items-center gap-2 text-sm mt-3 px-1", "style": "color: #3A4A38"},
          h("span", {"class_": "w-3 h-3 rounded-full bg-[#E41212] flex-shrink-0", "aria_hidden": "true"}),
          t("compareCaption")),
    )


def About(info):
    t = _get_t()
    rows = [(t("cleanAcc"), _g(info, "clean_accuracy")), (t("fieldAcc"), _g(info, "field_accuracy"))]
    return h(
        "details", {"class_": "group bg-white border border-[#DDD8CE] rounded-2xl"},
        h("summary", {"class_": "flex items-center justify-between gap-3 min-h-12 px-4 py-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden rounded-2xl"},
          h("span", {"class_": "text-sm font-bold text-[#1A201A]", "style": display}, t("about")),
          h("svg", {"width": "18", "height": "18", "viewBox": "0 0 24 24", "fill": "none", "stroke": "#2D6A4F", "stroke_width": "2.5", "stroke_linecap": "round",
                    "class_": "transition-transform duration-200 group-open:rotate-180", "aria_hidden": "true"},
            h("path", {"d": "M6 9l6 6 6-6"}))),
        h("div", {"class_": "px-4 pb-4 space-y-2 text-sm text-[#3A4A38] leading-relaxed"},
          h("p", None, _g(info, "note")),
          [None if v is None else h("p", {"class_": "flex justify-between gap-3 border-t border-[#EEE9DF] pt-2"},
                                    h("span", None, label),
                                    h("span", {"class_": "font-bold text-[#1A201A]"}, fmt_pct(v)))
           for label, v in rows]),
    )


def Badge(tone, *children):
    c = TONES[tone]
    return h("span", {"class_": "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold",
                      "style": f"background-color: {c['bg']}; color: {c['fg']}; {display}"},
             CheckI(15) if tone == "good" else AlertI(15), *children)


def ResultsContent(task, result, on_learn=None, ring_state=None, slider_state=None, follow_up_state=None):
    """Handlers: scan:retry (retake / try another), on_learn is an action name forwarded to ScanFollowUp."""
    t = _get_t()
    top = _g(result, "top") or []
    best = top[0] if top else None
    is_produce = task == "produce"
    state = _g(result, "state")
    fruit = _g(result, "fruit")
    confident = _g(result, "confident")

    if state:
        rotten = _g(state, "name") == "rotten"
    else:
        rotten = bool(re.search(r"rotten", _g(best, "name") or "", re.I))
    healthy = (not rotten) if is_produce else is_healthy_name(f"{_g(best, 'label') or ''} {_g(best, 'name') or ''}")
    if not confident:
        tone = "unsure"
    elif is_produce:
        tone = "bad" if rotten else "good"
    else:
        tone = "good" if healthy else "warn"

    fruit_name = _g(fruit, "name")
    state_word = t(_g(state, "name")) if state else None
    if not confident:
        headline = t("notSure")
    elif is_produce and fruit_name and state_word:
        headline = f"{state_word} {fruit_name.lower()}"
    else:
        headline = _g(best, "name") or ""

    if best:
        ring_value = pct(_g(best, "prob"))
    elif state:
        ring_value = pct(_g(state, "prob"))
    else:
        ring_value = None
    ring_label = "" if ring_value is None else f"{round(ring_value)}%"

    if not confident:
        status_text = None
    elif is_produce:
        status_text = t("rotten") if rotten else t("fresh")
    else:
        status_text = t("healthy") if healthy else t("disease")
    advice, source, disclaimer = _g(result, "advice"), _g(result, "source"), _g(result, "disclaimer")
    has_treatment = task in ("leaf", "pest") and bool(confident) and bool(advice or source or disclaimer)
    images = _g(result, "images")

    unsure_box = not confident and h(
        "div", {"role": "alert", "class_": "rounded-2xl border border-[#F0C27A] bg-[#FFF4DC] p-4 space-y-3"},
        h("div", {"class_": "flex gap-3"},
          AlertI(22, "#8A4B00"),
          h("p", {"class_": "text-base font-bold text-[#6B3A00] leading-snug", "style": display}, t("lowConf"))),
        h("button", {"data_action": "scan:retry", "class_": primaryBtn, "style": display}, CameraI(20, "#fff"), t("retake")))

    badges = is_produce and (fruit or state) and h(
        "div", {"class_": "flex flex-wrap gap-2 mt-4"},
        fruit and Badge("bad" if rotten else "good", f"{t('fruit')}: ", _g(fruit, "name"), f" {fmt_pct(_g(fruit, 'prob'))}"),
        state and Badge("bad" if _g(state, "name") == "rotten" else "good", f"{t('condition')}: ", t(_g(state, "name")), f" {fmt_pct(_g(state, 'prob'))}"))

    treatment = has_treatment and h(
        "section", {"class_": "bg-[#EEF5EF] border border-[#CFE3D5] rounded-2xl p-4 space-y-2.5"},
        h("div", {"class_": "flex items-center gap-2"},
          h("span", {"class_": "w-8 h-8 rounded-full bg-[#2D6A4F] flex items-center justify-center flex-shrink-0"}, LeafI(16, "#fff")),
          h("h3", {"class_": "text-sm font-bold text-[#1A201A]", "style": display}, t("treatment"))),
        advice and h("p", {"class_": "text-sm text-[#2E3F2E] leading-relaxed"}, advice),
        source and h("p", {"class_": "text-xs", "style": f"color: {MUTED}"}, f"{t('source')}: ", source),
        disclaimer and h("p", {"class_": "text-xs italic border-t border-[#CFE3D5] pt-2", "style": f"color: {MUTED}"}, disclaimer))

    return h(
        "div", {"class_": "space-y-4"},
        h("div", {"class_": "grid gap-4 lg:grid-cols-2 lg:gap-6 lg:items-start"},
          h("div", {"class_": "space-y-4 lg:order-2 animate-fade-up"},
            unsure_box,
            h("section", {"class_": "bg-white border border-[#DDD8CE] rounded-2xl p-4"},
              h("div", {"class_": "flex items-center gap-4"},
                ring_value is not None and ConfidenceRing(ring_value, tone, ring_label, ring_state),
                h("div", {"class_": "min-w-0 flex-1"},
                  h("p", {"class_": "text-xs font-semibold uppercase tracking-wide mb-0.5", "style": f"color: {MUTED}"}, t("result")),
                  h("h2", {"class_": "text-2xl font-extrabold text-[#1A201A] leading-tight break-words", "style": display}, headline),
                  status_text and h("span", {"class_": "inline-flex items-center gap-1.5 mt-2 rounded-full px-3 py-1 text-xs font-bold",
                                             "style": f"background-color: {TONES[tone]['bg']}; color: {TONES[tone]['fg']}; {display}"},
                                    CheckI(14) if healthy else AlertI(14), status_text),
                  (not confident and best) and h("p", {"class_": "text-sm mt-1", "style": f"color: {MUTED}"},
                                                 f"{t('closest')}: ", h("span", {"class_": "font-semibold text-[#3A4A38]"}, _g(best, "name"))))),
              badges),
            TopBars(result, tone)),
          h("div", {"class_": "space-y-4 lg:order-1 animate-fade-up", "style": "animation-delay: 120ms"},
            CompareSlider(_g(images, "photo"), _g(images, "heatmap"), slider_state),
            treatment,
            About(_g(result, "model_info")))),
        (confident and best) and scan_follow_up(
            follow_up_state or ScanFollowUpState(), task=task, label=headline if is_produce else _g(best, "name"),
            confidence=pct(_g(best, "prob")), is_healthy=healthy, on_learn=on_learn),
        confident and h("button", {"data_action": "scan:retry", "class_": primaryBtn, "style": display}, RetryI(18, "#fff"), t("tryAnother")),
        h("p", {"class_": "flex items-start gap-2 text-xs leading-relaxed", "style": f"color: {MUTED}"}, AlertI(14), t("mistakes")),
    )


# -- Error / empty -------------------------------------------------------------


def ErrorContent(error, can_retry_same):
    """Handlers: scan:retry-same, scan:reset."""
    t = _get_t()
    kind = _g(error, "kind") or "server"
    copy = {
        "unreadable": [t("errUnreadable"), t("errUnreadableBody")],
        "empty": [t("errEmpty"), t("errEmptyBody")],
        "network": [t("errNetwork"), t("errNetworkBody")],
        "server": [t("errServer"), t("errServerBody")],
    }[kind]
    transient = kind in ("network", "server") and can_retry_same
    soft = kind == "empty"
    if transient:
        buttons = [
            h("button", {"data_action": "scan:retry-same", "class_": primaryBtn, "style": display}, RetryI(18, "#fff"), t("tryAgain")),
            h("button", {"data_action": "scan:reset", "class_": secondaryBtn, "style": display}, t("chooseAnother")),
        ]
    else:
        buttons = h("button", {"data_action": "scan:reset", "class_": primaryBtn, "style": display}, RetryI(18, "#fff"), t("chooseAnother"))
    return h(
        "div", {"role": "alert", "class_": "flex flex-col items-center justify-center py-16 text-center animate-fade-up"},
        h("div", {"class_": f"w-20 h-20 rounded-full flex items-center justify-center mb-6 animate-shake {'bg-[#E8E4DB]' if soft else 'bg-[#FCE4E4]'}"},
          CameraI(34, "#3A4A38") if soft else AlertI(34, "#A81F1F")),
        h("h2", {"class_": "text-xl font-extrabold text-[#1A201A] mb-2", "style": display}, copy[0]),
        h("p", {"class_": "text-sm leading-relaxed mb-8 max-w-xs", "style": f"color: {MUTED}"}, copy[1]),
        h("div", {"class_": "w-full max-w-xs space-y-3"}, buttons),
    )
