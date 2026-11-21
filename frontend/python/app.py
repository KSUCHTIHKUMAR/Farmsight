"""Port of src/App.tsx. Components are functions returning HTML strings.

useState -> small state classes; handlers -> data-action attributes
(data-action="app:..." plus data-* payload attributes).
"""
import asyncio
import inspect

from python.h import h
from python.hub.farm_tools import farm_tools
from python.hub.overview import overview
from python.hub.ui import TOOLS, tool_icon
from python.lib.api import AnalyseError, analyse
from python.lib.i18n import lang_provider, use_t
from python.scan.scan_views import (
    ErrorContent, InputMethodContent, InputState, LoadingContent, LoadingState,
    ResultsContent,
)

DISPLAY = "font-family: Manrope, sans-serif"


def _g(o, k, default=None):
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


# -- Media query hook ----------------------------------------------------------


class IsDesktopState:
    """useIsDesktop: matches (min-width: 768px)."""

    def __init__(self, width=1024):
        self.width = width

    @property
    def is_desktop(self):
        return self.width >= 768


# -- SVG icons -----------------------------------------------------------------


def LeafIcon(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M12 2C6.5 2 3 6 3 12c0 4.5 3 8 9 9 1-3 1-6 0-8.5C9.5 10 7 10 7 10s1-4 5-4c3.5 0 7 2 7 8 0 3.5-2 6-4 7h-1c6-1 8-5 8-9 0-6-4-10-10-10z", "fill": color}))


def BugIcon(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round", "stroke_linejoin": "round"},
             h("ellipse", {"cx": "12", "cy": "14", "rx": "4", "ry": "5.5", "fill": color, "fill_opacity": "0.2"}),
             h("path", {"d": "M9 8.5c0-1.7 1.3-3 3-3s3 1.3 3 3M10 5L8.5 3M14 5l1.5-2M8 12H4M16 12h4M8.5 16L5 18M15.5 16l3.5 2M12 9v10"}))


def AppleIcon(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M17 8c-.5-1.5-2-3-4-3s-3.5 1.5-4 3c-1.5.5-3 2-3 5 0 4 2 7 5 7 .7 0 1.3-.3 2-.3s1.3.3 2 .3c3 0 5-3 5-7 0-3-1.5-4.5-3-5zm-2-4c.5-.7 1-1.5 1-2.5-.8.2-2 .8-2.5 2 .5-.1 1 .5 1.5.5z", "fill": color}))


def CameraIcon(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2v11z", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round", "stroke_linejoin": "round"}),
             h("circle", {"cx": "12", "cy": "13", "r": "4", "stroke": color, "stroke_width": "1.8"}))


def UploadIcon(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round", "stroke_linejoin": "round"}))


def ArrowRight(size=20, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M5 12h14M12 5l7 7-7 7", "stroke": color, "stroke_width": "2", "stroke_linecap": "round", "stroke_linejoin": "round"}))


def HomeIcon(size=20, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5z", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round", "stroke_linejoin": "round"}))


def ChevronLeft(size=20, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("path", {"d": "M15 18l-6-6 6-6", "stroke": color, "stroke_width": "2", "stroke_linecap": "round", "stroke_linejoin": "round"}))


def AlertCircle(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("circle", {"cx": "12", "cy": "12", "r": "10", "stroke": color, "stroke_width": "1.8"}),
             h("line", {"x1": "12", "y1": "8", "x2": "12", "y2": "12", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round"}),
             h("line", {"x1": "12", "y1": "16", "x2": "12.01", "y2": "16", "stroke": color, "stroke_width": "2", "stroke_linecap": "round"}))


def CheckCircle(size=24, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("circle", {"cx": "12", "cy": "12", "r": "10", "stroke": color, "stroke_width": "1.8"}),
             h("path", {"d": "M8 12l3 3 5-5", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round", "stroke_linejoin": "round"}))


def ScanIcon(size=16, color="currentColor"):
    return h("svg", {"width": size, "height": size, "viewBox": "0 0 24 24", "fill": "none"},
             h("circle", {"cx": "12", "cy": "12", "r": "3", "stroke": color, "stroke_width": "1.8"}),
             h("path", {"d": "M3 9V5a2 2 0 0 1 2-2h4M3 15v4a2 2 0 0 0 2 2h4M21 9V5a2 2 0 0 0-2-2h-4M21 15v4a2 2 0 0 1-2 2h-4", "stroke": color, "stroke_width": "1.8", "stroke_linecap": "round"}))


# -- Botanical decoration ------------------------------------------------------

LEAF = "M0 0C8 -11 22 -11 32 0C22 11 8 11 0 0Z"


def LeafSprig(class_name="", color="#52B788", opacity=1):
    leaves = [
        (40, 150, -60, 0.9), (52, 128, 50, 0.9), (64, 104, -55, 1), (74, 82, 48, 1),
        (84, 60, -50, 0.9), (92, 40, 45, 0.8), (100, 20, -70, 0.7),
    ]
    return h(
        "svg", {"aria_hidden": True, "viewBox": "0 0 140 180", "fill": "none",
                "class_": f"pointer-events-none select-none {class_name}", "style": f"opacity: {opacity}"},
        h("path", {"d": "M30 178C34 130 70 80 108 8", "stroke": color, "stroke_width": "2.2", "stroke_linecap": "round"}),
        [h("path", {"d": LEAF, "fill": color, "transform": f"translate({x} {y}) rotate({rot}) scale({sc})"}) for x, y, rot, sc in leaves],
        h("path", {"d": LEAF, "fill": color, "transform": "translate(108 8) rotate(-95) scale(0.9)"}),
    )


def Eyebrow(*children, light=False):
    return h("p", {"class_": f"flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] mb-3 {'text-[#95D5B2]' if light else 'text-[#2D6A4F]'}"},
             LeafIcon(13, "#95D5B2" if light else "#52B788"), *children)


# -- Panel state manager (shared logic for both layouts) -----------------------


class PanelManager:
    """usePanelManager. panel_state: 'input' | 'loading' | 'results' | 'error'."""

    def __init__(self, task):
        self.panel_state = "input"
        self.result = None
        self.error = None
        self.uploaded_image = None
        self.task = task  # taskRef.current
        self.file = None  # fileRef
        self.run_id = 0
        self.input_state = InputState()
        self.loading_state = LoadingState()

    @property
    def has_file(self):
        return bool(self.file)

    def clear_preview(self):
        # blob: URLs have no Python equivalent; just drop the reference.
        self.uploaded_image = None

    def run(self, file):
        self.run_id += 1
        rid = self.run_id
        self.error = None
        self.panel_state = "loading"
        self.loading_state = LoadingState()
        try:
            res = analyse(self.task, file)
            if inspect.isawaitable(res):
                res = asyncio.run(res)
            if rid != self.run_id:
                return
            self.result = res
            self.panel_state = "results"
        except Exception as e:  # noqa: BLE001
            if rid != self.run_id:
                return
            self.error = e if isinstance(e, AnalyseError) else AnalyseError("server")
            self.panel_state = "error"

    def handle_capture(self, file, preview_url=None):
        self.file = file
        self.clear_preview()
        self.uploaded_image = preview_url
        self.run(file)

    def handle_retry_same(self):
        if self.file:
            self.run(self.file)

    def handle_retry(self):
        self.run_id += 1
        self.file = None
        self.clear_preview()
        self.result = None
        self.error = None
        self.panel_state = "input"
        self.input_state = InputState()


# -- Desktop layout ------------------------------------------------------------

TASK_META = {
    "leaf": {"label": "Diagnose Leaf", "subtitle": "12 crops"},
    "produce": {"label": "Grade Produce", "subtitle": "14 crops"},
    "pest": {"label": "Identify Pest", "subtitle": "Tomato only"},
}


def use_task_meta():
    t = _get_t()
    return {
        "leaf": {"label": t("diagnoseLeaf"), "subtitle": TASK_META["leaf"]["subtitle"]},
        "produce": {"label": t("gradeProduce"), "subtitle": TASK_META["produce"]["subtitle"]},
        "pest": {"label": t("identifyPest"), "subtitle": TASK_META["pest"]["subtitle"]},
    }


def _tool(tool_id):
    return next((x for x in TOOLS if _g(x, "id") == tool_id), None)


def DesktopSidebar(active_task, panel_state, tool):
    """Handlers: app:home, app:task-select (data-task), app:open-tool (data-tool)."""
    task_meta = use_task_meta()

    task_buttons = []
    for t in ("leaf", "produce", "pest"):
        meta = task_meta[t]
        is_active = not tool and active_task == t
        task_buttons.append(h(
            "button", {"data_action": "app:task-select", "data_task": t, "title": meta["label"], "aria_label": meta["label"],
                       "class_": f"w-full text-left px-2 lg:px-3 py-3 rounded-xl flex items-center justify-center lg:justify-start gap-3 transition-colors duration-150 {'bg-white' if is_active else 'hover:bg-white/10'}"},
            h("div", {"class_": f"w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors duration-150 {'bg-[#D8EFDF]' if is_active else 'bg-white/10'}"},
              LeafIcon(16, "#2D6A4F" if is_active else "white") if t == "leaf" else BugIcon(16, "#8A4A1C" if is_active else "white") if t == "pest" else AppleIcon(16, "#E07B39" if is_active else "white")),
            h("div", {"class_": "min-w-0 hidden lg:block"},
              h("p", {"class_": f"text-sm font-semibold truncate {'text-[#2D6A4F]' if is_active else 'text-white'}", "style": DISPLAY}, meta["label"]),
              h("p", {"class_": f"text-xs truncate {'text-[#5A6A59]' if is_active else 'text-white/80'}"}, meta["subtitle"]))))

    tool_buttons = []
    for t in TOOLS:
        tid = _g(t, "id")
        on = tool == tid
        tool_buttons.append(h(
            "button", {"data_action": "app:open-tool", "data_tool": tid, "title": _g(t, "label"), "aria_label": _g(t, "label"),
                       "aria_current": "page" if on else None,
                       "class_": f"w-full text-left px-2 lg:px-3 py-2.5 rounded-xl flex items-center justify-center lg:justify-start gap-3 transition-colors duration-150 {'bg-white' if on else 'hover:bg-white/10'}"},
            h("div", {"class_": f"w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 {'bg-[#D8EFDF]' if on else 'bg-white/10'}"},
              tool_icon(tid, color="#2D6A4F" if on else "white")),
            h("div", {"class_": "min-w-0 hidden lg:block"},
              h("p", {"class_": f"text-sm font-semibold truncate {'text-[#2D6A4F]' if on else 'text-white'}", "style": DISPLAY}, _g(t, "label")),
              h("p", {"class_": f"text-xs truncate {'text-[#5A6A59]' if on else 'text-white/80'}"}, _g(t, "subtitle")))))

    return h(
        "div", {"class_": "w-[4.5rem] lg:w-56 flex-none flex flex-col bg-[#2D6A4F] text-white h-dvh sticky top-0 overflow-hidden"},
        # Brand
        h("button", {"data_action": "app:home", "aria_label": "FarmSight home",
                     "class_": "text-left px-3 lg:px-5 pt-8 pb-5 border-b border-white/10 hover:bg-white/5 transition-colors duration-150"},
          h("div", {"class_": "flex items-center justify-center lg:justify-start gap-2.5 mb-1"},
            h("div", {"class_": "w-7 h-7 bg-[#52B788] rounded-full flex items-center justify-center flex-shrink-0"}, LeafIcon(14, "white")),
            h("span", {"class_": "hidden lg:inline font-bold text-base", "style": DISPLAY}, "FarmSight")),
          h("p", {"class_": "hidden lg:block text-white/80 text-xs pl-[36px]"}, "AI-powered field analysis")),
        # Nav
        h("nav", {"class_": "flex-1 px-2 lg:px-3 py-5 space-y-1 overflow-y-auto"},
          h("button", {"data_action": "app:home",
                       "class_": "w-full text-left px-2 lg:px-3 py-2.5 rounded-xl flex items-center justify-center lg:justify-start gap-3 hover:bg-white/10 transition-colors duration-150 mb-4"},
            h("div", {"class_": "w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0"}, HomeIcon(16, "white")),
            h("span", {"class_": "hidden lg:inline text-sm font-semibold", "style": DISPLAY}, "Home")),
          h("p", {"class_": "hidden lg:block text-white/80 text-[10px] font-bold uppercase tracking-wider px-2 mb-3"}, "Tasks"),
          task_buttons,
          h("p", {"class_": "hidden lg:block text-white/80 text-[10px] font-bold uppercase tracking-wider px-2 pt-4 mb-3"}, "Knowledge & farm"),
          h("div", {"class_": "lg:hidden border-t border-white/10 my-3"}),
          tool_buttons),
        # Status indicator
        h("div", {"class_": "px-3 lg:px-5 py-4 border-t border-white/10"},
          h("div", {"class_": "flex items-center justify-center lg:justify-start gap-2"},
            h("div", {"class_": f"w-2 h-2 rounded-full flex-shrink-0 {'bg-[#52B788] animate-pulse-dot' if panel_state == 'loading' else 'bg-[#52B788]'}"}),
            h("p", {"class_": "hidden lg:block text-white/80 text-xs"}, "Processing…" if panel_state == "loading" else "Model ready"))),
    )


class DesktopState:
    """useState trio from DesktopApp plus its panel manager."""

    def __init__(self):
        self.active_task = "leaf"
        self.tool = None
        self.focus = {}
        self.panel = PanelManager(self.active_task)

    def open_tool(self, tool, crop_id=None):
        self.focus = {"crop_id": crop_id}
        self.tool = tool

    def open_scan(self, t):
        self.tool = None
        if t != self.active_task:
            self.active_task = t
            self.panel.task = t
            self.panel.handle_retry()

    def handle_learn(self, crop_id, disease_id, label):
        self.focus = {"crop_id": crop_id, "disease_id": disease_id, "scan_label": label}
        self.tool = "care"

    def handle_task_switch(self, t):
        if self.tool:
            self.tool = None
            if t == self.active_task:
                return
        if t == self.active_task:
            return
        self.active_task = t
        self.panel.task = t
        self.panel.handle_retry()


def DesktopApp(state):
    """Handlers: app:home, app:retry (New analysis), plus those of children."""
    task_meta = use_task_meta()
    tr = _get_t()
    panel = state.panel
    tool = state.tool
    active_task = state.active_task
    tool_info = _tool(tool) if tool else None

    new_analysis = (not tool and panel.panel_state not in ("input", "loading")) and h(
        "button", {"data_action": "app:retry",
                   "class_": "flex items-center gap-2 text-sm font-semibold text-[#1F5A41] bg-[#D8EFDF] hover:bg-[#C3E5CC] min-h-11 px-4 py-2 rounded-xl transition-colors",
                   "style": DISPLAY},
        h("svg", {"width": "14", "height": "14", "viewBox": "0 0 24 24", "fill": "none"},
          h("path", {"d": "M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15", "stroke": "#2D6A4F", "stroke_width": "2", "stroke_linecap": "round", "stroke_linejoin": "round"})),
        tr("newAnalysis"))

    content = None
    if panel.panel_state == "input":
        content = InputMethodContent(active_task, panel.input_state)
    elif panel.panel_state == "loading":
        content = LoadingContent(panel.uploaded_image, panel.loading_state)
    elif panel.panel_state == "results" and panel.result:
        content = ResultsContent(active_task, panel.result, on_learn="app:learn")
    elif panel.panel_state == "error":
        content = ErrorContent(panel.error, panel.has_file)

    return h(
        "div", {"class_": "relative flex h-dvh bg-gradient-to-br from-[#E3F1E7] via-[#F5F2EC] to-[#F5F2EC] overflow-hidden"},
        DesktopSidebar(active_task, panel.panel_state, tool),
        # Working panel
        h("div", {"class_": "flex-1 flex flex-col overflow-hidden"},
          # Panel header
          h("div", {"class_": "flex-none flex items-center justify-between gap-3 px-[clamp(1rem,3vw,2rem)] pt-[clamp(1.25rem,3vw,2rem)] pb-4 border-b border-[#DDD8CE] bg-[#F5F2EC]/70 backdrop-blur-sm"},
            h("div", None,
              h("h1", {"class_": "text-xl font-extrabold text-[#1A201A]", "style": DISPLAY},
                _g(tool_info, "label") if tool else task_meta[active_task]["label"]),
              h("p", {"class_": "text-xs text-[#5A6A59] mt-0.5"},
                _g(tool_info, "subtitle") if tool else task_meta[active_task]["subtitle"])),
            h("div", {"class_": "flex items-center gap-3"}, new_analysis)),
          # Scrollable content area
          LeafSprig("absolute bottom-0 right-0 w-40 xl:w-56 translate-x-6 translate-y-6 rotate-[-12deg]", "#52B788", 0.25),
          h("div", {"class_": "flex-1 overflow-y-auto px-[clamp(1rem,3vw,2rem)] py-[clamp(1.25rem,2.5vw,1.75rem)]"},
            tool and h("div", {"class_": "w-full max-w-3xl mx-auto animate-fade-in"},
                       farm_tools(tool=tool, focus=state.focus, on_tool="app:open-tool", on_scan="app:open-scan")),
            h("div", {"class_": f"w-full mx-auto animate-fade-in {'max-w-4xl' if panel.panel_state == 'results' else 'max-w-lg xl:max-w-xl'} {'hidden' if tool else ''}"},
              content))),
    )


# -- Mobile layout -------------------------------------------------------------


def TopBar(on_back=False, on_home=False, title=None, light=False):
    """Handlers: app:back, app:home (back/home flags say whether the button renders)."""
    btn_cls = "bg-white/15 hover:bg-white/25" if light else "bg-[#E8E4DB] hover:bg-[#DDD8CE]"
    icon_color = "white" if light else "#1A201A"
    back_action = on_back if isinstance(on_back, str) else "app:back"
    return h(
        "div", {"class_": f"flex items-center gap-3 px-[clamp(1rem,5vw,1.25rem)] pt-12 pb-4 {'text-white' if light else 'text-[#1A201A]'}"},
        on_back and h("button", {"data_action": back_action, "class_": f"flex items-center justify-center w-11 h-11 rounded-full transition-colors {btn_cls}", "aria_label": "Go back"},
                      ChevronLeft(18, icon_color)),
        title and h("span", {"class_": "text-sm font-semibold tracking-wide uppercase opacity-70", "style": DISPLAY}, title),
        h("div", {"class_": "ml-auto flex items-center gap-2"},
          on_home and h("button", {"data_action": "app:home", "class_": f"flex items-center justify-center w-11 h-11 rounded-full transition-colors {btn_cls}", "aria_label": "Home"},
                        HomeIcon(18, icon_color))),
    )


CROPS = [
    {"name": "Tomato", "note": "Leaf disease", "image": "https://images.unsplash.com/photo-1582284540020-8acbe03f4924?w=700&h=700&fit=crop&auto=format"},
    {"name": "Potato", "note": "Leaf disease", "image": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=700&h=700&fit=crop&auto=format"},
    {"name": "Apple", "note": "Fresh or rotten", "image": "https://images.unsplash.com/photo-1628486930972-c1db82d528da?w=700&h=700&fit=crop&auto=format"},
    {"name": "Orange", "note": "Fresh or rotten", "image": "https://images.unsplash.com/photo-1638450060428-112a559ac3c7?w=700&h=700&fit=crop&auto=format"},
]


def LandingHero():
    """Handler: app:start."""
    start_desktop = h("button", {"data_action": "app:start",
                                 "class_": "hidden md:flex items-center justify-center gap-3 bg-[#2D6A4F] text-white font-bold text-base px-8 py-4 rounded-2xl hover:bg-[#235a41] tap",
                                 "style": DISPLAY}, "Get Started", ArrowRight(18, "white"))
    start_mobile = h("button", {"data_action": "app:start",
                                "class_": "md:hidden mt-auto w-full flex items-center justify-center gap-3 bg-[#2D6A4F] text-white font-bold text-base py-4 rounded-2xl hover:bg-[#235a41] tap",
                                "style": DISPLAY}, "Get Started", ArrowRight(18, "white"))
    return h(
        "div", {"class_": "min-h-[85dvh] w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] pt-[clamp(1.5rem,6vw,4rem)] pb-8 flex flex-col md:flex-row md:items-center md:gap-[clamp(2rem,5vw,3.5rem)]"},
        h("div", {"class_": "md:flex-1 animate-fade-up"},
          h("div", {"class_": "flex items-center gap-2.5 mb-6 md:mb-8"},
            h("div", {"class_": "w-9 h-9 rounded-full bg-[#2D6A4F] flex items-center justify-center"}, LeafIcon(18, "white")),
            h("span", {"class_": "text-xl font-bold tracking-tight text-[#1A201A]", "style": DISPLAY}, "FarmSight")),
          h("h1", {"class_": "text-[clamp(1.875rem,7vw,3.25rem)] font-extrabold leading-[1.08] tracking-tight text-[#1A201A] mb-4", "style": DISPLAY},
            "Know your crop", h("br"), h("span", {"class_": "text-[#2D6A4F]"}, "before it shows.")),
          h("p", {"class_": "text-[#3A4A38] text-base leading-relaxed mb-6 md:max-w-md"},
            "Photograph a leaf from 12 crops to spot disease, grade 14 kinds of produce, or identify tomato pests — with a heatmap showing exactly what the AI saw."),
          h("div", {"class_": "flex flex-wrap gap-2 mb-8"},
            [h("span", {"class_": "flex items-center gap-1.5 text-xs font-medium text-[#2D6A4F] bg-[#D8EFDF] px-3 py-1.5 rounded-full"}, ScanIcon(12, "#2D6A4F"), t)
             for t in ("Heatmap explanations", "Treatment tips", "No account needed")]),
          start_desktop),
        h("div", {"class_": "md:flex-1 grid grid-cols-2 gap-3 md:gap-4 mb-8 md:mb-0"},
          [h("div", {"class_": f"relative rounded-3xl overflow-hidden aspect-[4/5] bg-[#E8E4DB] animate-fade-up {'translate-y-4' if i % 2 == 1 else ''}",
                     "style": f"animation-delay: {100 + i * 70}ms"},
             h("img", {"src": c["image"], "alt": c["name"], "class_": "absolute inset-0 w-full h-full object-cover"}),
             h("div", {"class_": "absolute inset-0", "style": "background: linear-gradient(to top, rgba(20,40,28,0.78) 0%, rgba(20,40,28,0) 55%)"}),
             h("div", {"class_": "absolute bottom-0 left-0 right-0 p-4 text-white"},
               h("p", {"class_": "text-lg font-extrabold leading-tight", "style": DISPLAY}, c["name"]),
               h("p", {"class_": "text-xs text-white/75"}, c["note"])))
           for i, c in enumerate(CROPS)]),
        start_mobile,
    )


STRIP = [
    {"name": "Tomato", "image": CROPS[0]["image"]},
    {"name": "Potato", "image": CROPS[1]["image"]},
    {"name": "Apple", "image": CROPS[2]["image"]},
    {"name": "Banana", "image": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=200&h=200&fit=crop&auto=format"},
    {"name": "Orange", "image": CROPS[3]["image"]},
]


def _steps():
    return [
        {"icon": CameraIcon(22, "#2D6A4F"), "title": "Snap a photo",
         "text": "Take a clear picture of a leaf or a piece of fruit, or upload one from your phone."},
        {"icon": ScanIcon(22, "#2D6A4F"), "title": "AI takes a look",
         "text": "A model tuned for your crop checks for disease or freshness in a few seconds."},
        {"icon": CheckCircle(22, "#2D6A4F"), "title": "Get a clear answer",
         "text": "See the result, how confident it is, and simple treatment guidance when it applies."},
    ]


def LandingScreen():
    """Handler: app:start."""
    return h(
        "div", {"class_": "relative overflow-hidden bg-gradient-to-b from-[#DCEFE1] via-[#EDF3E8] to-[#F5F2EC]"},
        LeafSprig("absolute top-6 -right-6 w-36 md:w-56 rotate-12", "#52B788", 0.35),
        LeafSprig("absolute top-[34rem] -left-8 w-28 md:w-44 -scale-x-100", "#2D6A4F", 0.18),
        h("div", {"aria_hidden": True, "class_": "absolute -top-32 -right-32 w-[28rem] h-[28rem] rounded-full bg-[#D8EFDF] opacity-70 blur-3xl pointer-events-none"}),
        h("div", {"aria_hidden": True, "class_": "absolute top-[40rem] -left-40 w-[26rem] h-[26rem] rounded-full bg-[#FDE8D8] opacity-60 blur-3xl pointer-events-none"}),
        h("div", {"class_": "relative"},
          LandingHero(),
          # Crop strip
          h("section", {"class_": "w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-8"},
            h("div", {"class_": "flex items-center gap-3 mb-4 text-[#2D6A4F]"},
              h("span", {"class_": "h-px flex-1 bg-[#B7DCC4]"}),
              LeafIcon(14, "#52B788"),
              h("span", {"class_": "text-[11px] font-bold uppercase tracking-[0.14em]"}, "Works with"),
              LeafIcon(14, "#52B788"),
              h("span", {"class_": "h-px flex-1 bg-[#B7DCC4]"})),
            h("div", {"class_": "flex flex-wrap justify-center gap-2.5"},
              [h("div", {"class_": "flex items-center gap-2 bg-white border border-[#DDD8CE] rounded-full pl-1 pr-4 py-1"},
                 h("img", {"src": c["image"], "alt": "", "class_": "w-8 h-8 rounded-full object-cover"}),
                 h("span", {"class_": "text-sm font-semibold text-[#1A201A]", "style": DISPLAY}, c["name"]))
               for c in STRIP])),
          # Explainability demo
          h("section", {"class_": "w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-10 md:py-16 flex flex-col md:flex-row md:items-center gap-8 md:gap-14"},
            h("div", {"class_": "md:flex-1 relative rounded-3xl overflow-hidden aspect-square bg-[#1A201A] shadow-[0_20px_50px_-20px_rgba(26,32,26,0.45)]"},
              h("img", {"src": "https://images.unsplash.com/photo-1642307321395-b72347cbe944?w=800&h=800&fit=crop&auto=format",
                        "alt": "Tomato leaf with AI heatmap", "class_": "w-full h-full object-cover opacity-80"}),
              h("div", {"aria_hidden": "true", "class_": "absolute inset-0 mix-blend-screen",
                        "style": "background: radial-gradient(circle at 54% 38%, rgba(228,18,18,.7), rgba(242,188,18,.4) 14%, rgba(48,210,72,.2) 24%, transparent 32%), radial-gradient(circle at 30% 64%, rgba(235,80,10,.55), rgba(242,188,18,.3) 10%, transparent 22%)"}),
              h("div", {"class_": "absolute top-3 left-3 flex items-center gap-1.5 bg-black/50 backdrop-blur-sm text-white text-xs font-medium px-2.5 py-1 rounded-lg"},
                h("span", {"class_": "w-1.5 h-1.5 rounded-full bg-[#E41212] animate-pulse-dot"}),
                "Example heatmap")),
            h("div", {"class_": "md:flex-1"},
              Eyebrow("Explainable by design"),
              h("h2", {"class_": "text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold leading-tight tracking-tight text-[#1A201A] mb-3", "style": DISPLAY},
                "See what the AI sees."),
              h("p", {"class_": "text-[#3A4A38] leading-relaxed md:max-w-md"},
                "Every result comes with a heatmap. Warm colours mark the exact spots that shaped the decision, so you can check the answer against what is in front of you."))),
          # How it works
          h("section", {"class_": "relative bg-[#2D6A4F] rounded-t-[2.5rem] md:rounded-t-[4rem] mt-6 overflow-hidden"},
            LeafSprig("absolute -top-4 -left-6 w-32 md:w-48 -rotate-12 -scale-x-100", "#52B788", 0.22),
            LeafSprig("absolute -bottom-6 -right-4 w-36 md:w-52 rotate-[160deg]", "#52B788", 0.22),
            h("div", {"class_": "relative w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-14 md:py-20"},
              h("div", {"class_": "md:flex md:flex-col md:items-center mb-8"},
                Eyebrow("How it works", light=True),
                h("h2", {"class_": "text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold tracking-tight text-white md:text-center", "style": DISPLAY},
                  "Three steps, no setup.")),
              h("div", {"class_": "grid gap-4 md:grid-cols-3"},
                [h("div", {"class_": "bg-white border border-[#DDD8CE] rounded-3xl p-5 card-lift"},
                   h("div", {"class_": "flex items-center justify-between mb-4"},
                     h("div", {"class_": "w-11 h-11 rounded-2xl bg-[#D8EFDF] flex items-center justify-center"}, st["icon"]),
                     h("span", {"class_": "text-3xl font-extrabold text-[#E8E4DB]", "style": DISPLAY}, f"0{i + 1}")),
                   h("h3", {"class_": "font-bold text-[#1A201A] mb-1", "style": DISPLAY}, st["title"]),
                   h("p", {"class_": "text-sm text-[#5A6A59] leading-relaxed"}, st["text"]))
                 for i, st in enumerate(_steps())]))),
          # CTA banner
          h("section", {"class_": "w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] py-12"},
            h("div", {"class_": "relative rounded-3xl overflow-hidden"},
              h("img", {"src": "https://images.unsplash.com/photo-1524486361537-8ad15938e1a3?w=1400&h=700&fit=crop&auto=format",
                        "alt": "Rows of tomato plants in a greenhouse", "class_": "absolute inset-0 w-full h-full object-cover"}),
              h("div", {"class_": "absolute inset-0 bg-gradient-to-r from-[#143420]/90 via-[#143420]/70 to-[#143420]/30"}),
              h("div", {"class_": "relative p-[clamp(1.5rem,5vw,3rem)] text-white md:max-w-lg"},
                h("h2", {"class_": "text-[clamp(1.5rem,4.5vw,2.25rem)] font-extrabold leading-tight tracking-tight mb-2", "style": DISPLAY},
                  "Catch problems early."),
                h("p", {"class_": "text-white/80 leading-relaxed mb-5"}, "Spot disease before it spreads and sort fruit before it spoils."),
                h("button", {"data_action": "app:start",
                             "class_": "inline-flex items-center gap-3 bg-white text-[#2D6A4F] font-bold px-7 py-3.5 rounded-2xl hover:bg-[#F5F2EC] tap",
                             "style": DISPLAY}, "Start analysing", ArrowRight(18, "#2D6A4F"))))),
          h("footer", {"class_": "w-full max-w-xl md:max-w-5xl mx-auto px-[clamp(1rem,5vw,2.5rem)] pt-4 pb-10 text-center"},
            h("div", {"class_": "flex justify-center gap-2 mb-3 opacity-60"},
              LeafIcon(12, "#52B788"), LeafIcon(16, "#2D6A4F"), LeafIcon(12, "#52B788")),
            h("p", {"class_": "text-xs text-[#5A6A59] leading-relaxed"},
              "FarmSight can make mistakes and can't be 100% sure about any result. Use it as a guide and confirm important decisions with an expert."))),
    )


class TaskPickerState:
    """useState<Task | null> picked; the TS version calls onSelect after 240 ms."""

    def __init__(self):
        self.picked = None

    def handle_pick(self, task_id):
        if self.picked:
            return False
        self.picked = task_id
        return True  # caller should dispatch app:task-picked after 240 ms


PRODUCE_CROPS = ["Apple", "Banana", "Bell pepper", "Carrot", "Cucumber", "Grape", "Guava", "Jujube",
                 "Mango", "Orange", "Pomegranate", "Potato", "Strawberry", "Tomato"]
LEAF_CROPS = ["Apple", "Bell pepper", "Cucumber", "Grape", "Groundnut", "Jute", "Maize", "Mango",
              "Onion", "Potato", "Tomato", "Turmeric"]
PEST_CROPS = ["Tomato"]


def TaskPickerScreen(state=None):
    """Handlers: app:pick-task (data-task), app:open-tool (data-tool), app:back, app:home."""
    state = state or TaskPickerState()
    options = [
        {"id": "leaf", "label": "Diagnose Leaf",
         "desc": "Detect diseases on the leaves of 12 crops, from early blight in tomato and potato to problems in maize, jute and groundnut. Tomato pests can also be identified.",
         "chips": LEAF_CROPS, "iconBg": "#D8EFDF", "iconHover": "#B6DFC5", "icon": LeafIcon(28, "#2D6A4F")},
        {"id": "produce", "label": "Grade Produce",
         "desc": "Grade 14 kinds of fruit and vegetables as fresh or rotten to reduce waste and improve quality.",
         "chips": PRODUCE_CROPS, "iconBg": "#FDE8D8", "iconHover": "#F8C9A8", "icon": AppleIcon(28, "#E07B39")},
        {"id": "pest", "label": "Identify Pest",
         "desc": "Identify common tomato pests such as whiteflies, aphids and mites from a close-up photo, with management tips.",
         "chips": PEST_CROPS, "iconBg": "#F1E3D3", "iconHover": "#E6CFB4", "icon": BugIcon(28, "#8A4A1C")},
    ]
    cards = []
    for o in options:
        cards.append(h(
            "button", {"data_action": "app:pick-task", "data_task": o["id"],
                       "class_": f"w-full text-left bg-white border-2 border-[#DDD8CE] hover:border-[#52B788] rounded-2xl p-5 flex gap-4 items-start card-lift group {'animate-select-pulse' if state.picked == o['id'] else ''}"},
            h("div", {"class_": "w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 transition-colors",
                      "style": f"background-color: {o['iconBg']}",
                      "data_hover_bg": o["iconHover"], "data_base_bg": o["iconBg"]},
              o["icon"]),
            h("div", {"class_": "flex-1 pt-0.5"},
              h("h3", {"class_": "text-lg font-bold text-[#1A201A] mb-1", "style": DISPLAY}, o["label"]),
              h("p", {"class_": "text-sm text-[#5A6A59] leading-relaxed"}, o["desc"]),
              h("div", {"class_": "flex gap-1.5 mt-3 flex-wrap"},
                [h("span", {"class_": "text-xs font-medium bg-[#F5F2EC] text-[#3A4A38] border border-[#DDD8CE] px-2 py-0.5 rounded-full"}, c) for c in o["chips"]])),
            h("div", {"class_": "self-center opacity-30 group-hover:opacity-100 transition-opacity"}, ArrowRight(16, "#2D6A4F"))))
    return h(
        "div", {"class_": "flex flex-col min-h-dvh animate-fade-up"},
        TopBar(on_back=True, on_home=True, title="Choose Task"),
        h("div", {"class_": "flex-1 px-5 pt-2 pb-10"},
          h("div", {"class_": "mb-7"},
            h("h2", {"class_": "text-2xl font-extrabold text-[#1A201A] mb-1", "style": DISPLAY},
              "What are you", h("br"), "analysing today?"),
            h("p", {"class_": "text-sm text-[#5A6A59]"}, "Each option runs a separate AI model tuned for that task.")),
          h("div", {"class_": "space-y-4"}, cards),
          h("div", {"class_": "mt-9"},
            h("h3", {"class_": "text-lg font-extrabold text-[#1A201A] mb-1", "style": DISPLAY}, "Knowledge & farm tools"),
            h("p", {"class_": "text-sm text-[#5A6A59] mb-4"}, "Crop profiles, care guidance, task planning and your journal."),
            overview([], show_scan=False),
            h("div", {"class_": "grid grid-cols-2 gap-2 mt-3"},
              [h("button", {"data_action": "app:open-tool", "data_tool": _g(t, "id"),
                            "class_": "tap flex items-center gap-2 bg-white border border-[#DDD8CE] rounded-xl px-3 py-3 text-sm font-semibold text-[#1A201A]",
                            "style": DISPLAY},
                  tool_icon(_g(t, "id"), color="#2D6A4F"), _g(t, "label"))
               for t in TOOLS if _g(t, "id") not in ("overview", "hub")]))),
    )


class MobileState:
    """MobileApp useState set + panel manager. mobile_screen: landing | task-picker | working | tool."""

    def __init__(self):
        self.mobile_screen = "landing"
        self.task = "leaf"
        self.tool = "overview"
        self.focus = {}
        self.panel = PanelManager(self.task)
        self.picker = TaskPickerState()

    def open_tool(self, t, crop_id=None):
        self.focus = {"crop_id": crop_id}
        self.tool = t
        self.mobile_screen = "tool"

    def handle_learn(self, crop_id, disease_id, label):
        self.focus = {"crop_id": crop_id, "disease_id": disease_id, "scan_label": label}
        self.tool = "care"
        self.mobile_screen = "tool"

    def handle_task_select(self, t):
        self.task = t
        self.panel.task = t
        self.mobile_screen = "working"
        self.panel.handle_retry()
        self.picker = TaskPickerState()

    def handle_home(self):
        self.mobile_screen = "landing"
        self.panel.handle_retry()

    def handle_back(self):
        if self.mobile_screen == "working":
            self.mobile_screen = "task-picker"
            self.panel.handle_retry()
        elif self.mobile_screen == "tool":
            self.mobile_screen = "task-picker"
        elif self.mobile_screen == "task-picker":
            self.mobile_screen = "landing"


def MobileApp(state):
    task_meta = use_task_meta()
    tr = _get_t()
    panel = state.panel
    screen = state.mobile_screen
    task = state.task

    parts = []
    if screen == "landing":
        parts.append(LandingScreen())
    if screen == "task-picker":
        parts.append(TaskPickerScreen(state.picker))
    if screen == "tool":
        tool_info = _tool(state.tool)
        parts.append(h(
            "div", {"class_": "flex flex-col min-h-dvh animate-fade-up"},
            TopBar(on_back=True, on_home=True, title=_g(tool_info, "label") or "Tools"),
            h("div", {"class_": "flex-1 px-5 pt-2 pb-10"},
              farm_tools(tool=state.tool, focus=state.focus, on_tool="app:open-tool"))))
    if screen == "working":
        if panel.panel_state == "input":
            parts.append(h(
                "div", {"class_": "flex flex-col min-h-dvh animate-fade-up"},
                TopBar(on_back=True, on_home=True, title=task_meta[task]["label"]),
                h("div", {"class_": "flex-1 px-5 pt-2 pb-10"}, InputMethodContent(task, panel.input_state))))
        if panel.panel_state == "loading":
            parts.append(h(
                "div", {"class_": "flex flex-col min-h-dvh animate-fade-in px-[clamp(1rem,5vw,1.25rem)] pt-12"},
                LoadingContent(panel.uploaded_image, panel.loading_state)))
        if panel.panel_state == "results" and panel.result:
            parts.append(h(
                "div", {"class_": "flex flex-col min-h-dvh animate-fade-up"},
                TopBar(on_back="app:retry", on_home=True, title=tr("result")),
                h("div", {"class_": "flex-1 overflow-y-auto px-5 pt-1 pb-10"},
                  ResultsContent(task, panel.result, on_learn="app:learn"))))
        if panel.panel_state == "error":
            parts.append(h(
                "div", {"class_": "flex flex-col min-h-dvh animate-fade-in"},
                h("div", {"class_": "px-5 pt-2"}, ErrorContent(panel.error, panel.has_file))))

    return h(
        "div", {"class_": "relative min-h-dvh bg-gradient-to-b from-[#E3F1E7] via-[#F5F2EC] to-[#F5F2EC] flex flex-col overflow-hidden"},
        LeafSprig("absolute top-2 -right-8 w-32 rotate-12", "#52B788", 0.28),
        h("div", {"class_": "relative flex-1 w-full max-w-xl mx-auto flex flex-col"}, parts))


# -- Root ----------------------------------------------------------------------


class AppState:
    """Root state: viewport + `started` + the desktop/mobile sub-states."""

    def __init__(self, width=1024):
        self.viewport = IsDesktopState(width)
        self.started = False
        self.desktop = DesktopState()
        self.mobile = MobileState()


def AppInner(state):
    if state.viewport.is_desktop and not state.started:
        return h("div", {"class_": "bg-[#F5F2EC] min-h-dvh"}, LandingScreen())
    return DesktopApp(state.desktop) if state.viewport.is_desktop else MobileApp(state.mobile)


def App(state=None):
    state = state or AppState()
    return lang_provider(AppInner(state))


default = App
