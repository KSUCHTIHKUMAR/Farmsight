"""Port of src/hub/ScanFollowUp.tsx."""
from python.h import h
from python.hub.crops import crop_for_label, match_scan_label
from python.hub.store import add_journal_entry
from python.hub.ui import act, display, get_crop, style, w

from python.hub.planner import today_iso


class ScanFollowUpState:
    def __init__(self):
        self.saved = False


def save(state, task, label, confidence):
    """onClick of the save button (data-action="scan-save")."""
    add_journal_entry({
        "date": today_iso(),
        "type": "scan",
        "crop": crop_for_label(label) or "",
        "title": f"{label} (AI suggestion)",
        "notes": f"{'Disease scan' if task == 'leaf' else 'Pest scan' if task == 'pest' else 'Produce check'}. Model confidence {confidence:.1f}%. Not a confirmed result.",
        "source": "scan",
        "ai_suggestion": True,
        "confirmed": False,
    })
    state.saved = True


def scan_follow_up(state, task, label, confidence, is_healthy, on_learn=True):
    """on_learn: truthy if the onLearn callback exists (button emits data-action="learn")."""
    link = w(match_scan_label(label)) if task == "leaf" and not is_healthy else None
    crop = get_crop(link.crop_id) if link else None
    saved = state.saved
    D = {"style": style(display)}

    learn = None
    if link and crop and on_learn:
        learn = h(
            "button",
            {**act("learn", crop_id=link.crop_id, disease_id=link.disease_id, label=label),
             "class_": "tap w-full text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] rounded-2xl px-4 py-3"},
            h("p", {"class_": "text-sm font-bold text-[#2D6A4F]", **D}, "Learn about this possible disease"),
            h("p", {"class_": "text-xs text-[#5A6A59]"},
              f"Symptoms and prevention for {crop.name.lower()}. The scan is a suggestion, not a confirmed diagnosis."),
        )

    return h(
        "div",
        {"class_": "space-y-2"},
        learn,
        h(
            "button",
            {**act("scan-save"), "disabled": saved or None,
             "class_": "tap w-full text-left bg-white border border-[#DDD8CE] hover:border-[#52B788] disabled:opacity-70 rounded-2xl px-4 py-3"},
            h("p", {"class_": "text-sm font-bold text-[#2D6A4F]", **D}, "Saved to Farm Journal" if saved else "Save to Farm Journal"),
            h("p", {"class_": "text-xs text-[#5A6A59]"},
              "Recorded as an unconfirmed AI suggestion in this browser." if saved else "Keep this result as an unconfirmed note in this browser."),
        ),
    )
