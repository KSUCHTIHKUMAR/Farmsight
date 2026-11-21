"""Port of src/hub/FarmTools.tsx."""
from python.h import h
from python.hub.calendar_view import calendar_view
from python.hub.care import care_guide
from python.hub.hub import knowledge_hub
from python.hub.journal import journal
from python.hub.overview import overview
from python.hub.ui import TOOLS, tool_banner


def farm_tools(tool, focus, states, plans, show_scan=True):
    """focus: dict with optional cropId/diseaseId/scanLabel (ToolFocus).
    states: dict of per-tool state objects keyed overview/hub/care/calendar/journal
    (create them fresh whenever the React `key` changes: tool + cropId + diseaseId)."""
    meta = next(t for t in TOOLS if t["id"] == tool)
    key = f"{tool}-{focus.get('cropId') or ''}-{focus.get('diseaseId') or ''}"
    body = None
    if tool == "overview":
        body = overview(plans, show_scan)
    elif tool == "hub":
        body = knowledge_hub(states["hub"])
    elif tool == "care":
        body = care_guide(states["care"], focus.get("cropId"), focus.get("diseaseId"), focus.get("scanLabel"))
    elif tool == "calendar":
        body = calendar_view(states["calendar"])
    elif tool == "journal":
        body = journal(states["journal"])
    return h("div", {"data_key": key}, tool_banner(tool, meta["label"], meta["subtitle"]), body)
