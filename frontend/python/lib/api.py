"""FarmSight analysis API client (port of src/lib/api.ts)."""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, Optional, TypedDict

Task = Literal["leaf", "produce", "pest"]


class TopGuess(TypedDict):
    label: str
    name: str
    prob: float


class NameProb(TypedDict):
    name: str
    prob: float


class Images(TypedDict):
    photo: str
    heatmap: str


class ModelInfo(TypedDict):
    note: str
    clean_accuracy: NotRequired[float]
    field_accuracy: NotRequired[float]


class AnalyseResult(TypedDict):
    task: Task
    confident: bool
    top: list[TopGuess]
    images: Images
    model_info: ModelInfo
    fruit: NotRequired[Optional[NameProb]]
    state: NotRequired[Optional[NameProb]]  # name is 'fresh' | 'rotten'
    advice: NotRequired[Optional[str]]
    source: NotRequired[Optional[str]]
    disclaimer: NotRequired[str]


AnalyseErrorKind = Literal["empty", "unreadable", "network", "server"]


class AnalyseError(Exception):
    def __init__(self, kind: AnalyseErrorKind, message: Optional[str] = None) -> None:
        super().__init__(message if message is not None else kind)
        self.kind: AnalyseErrorKind = kind


@dataclass
class UploadFile:
    """Stand-in for the browser File object."""
    name: str
    data: bytes
    type: str = ""

    @property
    def size(self) -> int:
        return len(self.data)


def pct(p: float) -> float:
    """Probabilities may arrive as 0-1 fractions or 0-100 percentages; this only normalises for display."""
    return p * 100 if p <= 1 else p


def fmt_pct(p: float) -> str:
    return f"{int(pct(p) + 0.5)}%"


def is_healthy_name(s: str) -> bool:
    return re.search(r"healthy|no pest", s, re.I) is not None


_env = os.environ.get("VITE_FARMSIGHT_API_URL")
ENDPOINT: Optional[str] = _env.rstrip("/") if _env and _env.rstrip("/") != "" else None
if _env and ENDPOINT is None:
    ENDPOINT = None


def is_result(x: Any) -> bool:
    if not isinstance(x, dict):
        return False
    images = x.get("images")
    info = x.get("model_info")
    return (
        x.get("task") in ("leaf", "produce", "pest")
        and isinstance(x.get("confident"), bool)
        and isinstance(x.get("top"), list)
        and bool(images)
        and isinstance(images.get("photo"), str)
        and isinstance(images.get("heatmap"), str)
        and bool(info)
        and isinstance(info.get("note"), str)
    )


def analyse(task: Task, file: Optional[UploadFile]) -> AnalyseResult:
    if file is None or file.size == 0:
        raise AnalyseError("empty")
    if file.type and not file.type.startswith("image/"):
        raise AnalyseError("unreadable")
    if not ENDPOINT:
        return demo_analyse(task, file)

    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="task"\r\n\r\n{task}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{file.name}"\r\n'
         f'Content-Type: {file.type or "application/octet-stream"}\r\n\r\n').encode() + file.data + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(
        f"{ENDPOINT}/analyse", data=b"".join(parts), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            status, raw = res.status, res.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, b""
    except (urllib.error.URLError, OSError):
        raise AnalyseError("network")
    if status in (415, 422):
        raise AnalyseError("unreadable")
    if not 200 <= status < 300:
        raise AnalyseError("server")
    try:
        js = json.loads(raw)
    except ValueError:
        js = None
    if not is_result(js):
        raise AnalyseError("server", "Unexpected response shape")
    if len(js["top"]) == 0:
        raise AnalyseError("empty")
    return js


# -- Demo adapter ------------------------------------------------------------
# Used only when VITE_FARMSIGHT_API_URL is not set, so every UI state can be reviewed.
# Everything it returns is a placeholder and says so in model_info.note.
# Force a state with the FARMSIGHT_DEMO env var (replaces ?demo=): early|healthy|lowconf|rotten|fresh|error|empty

DEMO_NOTE = (
    "Demo mode: no model server is connected (VITE_FARMSIGHT_API_URL is not set). "
    "The probabilities and heatmap below are placeholders, not a real prediction."
)


class Blob(TypedDict):
    x: float
    y: float
    r: float
    a: float


class Scenario(TypedDict):
    key: str
    task: Task
    confident: bool
    top: list[TopGuess]
    blobs: list[Blob]
    fruit: NotRequired[NameProb]
    state: NotRequired[NameProb]
    advice: NotRequired[str]


SCENARIOS: list[Scenario] = [
    {
        "key": "early",
        "task": "leaf",
        "confident": True,
        "top": [
            {"label": "Tomato___Early_blight", "name": "Tomato Early Blight", "prob": 0.914},
            {"label": "Tomato___Septoria_leaf_spot", "name": "Tomato Septoria Leaf Spot", "prob": 0.058},
            {"label": "Tomato___healthy", "name": "Healthy Tomato Leaf", "prob": 0.016},
        ],
        "advice": "Remove the affected leaves, keep foliage dry and improve airflow between plants. Ask your local agricultural extension office which fungicide is approved for your area.",
        "blobs": [
            {"x": 0.54, "y": 0.38, "r": 0.3, "a": 0.7},
            {"x": 0.3, "y": 0.62, "r": 0.2, "a": 0.52},
        ],
    },
    {
        "key": "lowconf",
        "task": "leaf",
        "confident": False,
        "top": [
            {"label": "Potato___Late_blight", "name": "Potato Late Blight", "prob": 0.41},
            {"label": "Tomato___Early_blight", "name": "Tomato Early Blight", "prob": 0.33},
            {"label": "Tomato___healthy", "name": "Healthy Tomato Leaf", "prob": 0.14},
        ],
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.34, "a": 0.45}],
    },
    {
        "key": "healthy",
        "task": "leaf",
        "confident": True,
        "top": [
            {"label": "Tomato___healthy", "name": "Healthy Tomato Leaf", "prob": 0.961},
            {"label": "Tomato___Early_blight", "name": "Tomato Early Blight", "prob": 0.024},
            {"label": "Tomato___Septoria_leaf_spot", "name": "Tomato Septoria Leaf Spot", "prob": 0.01},
        ],
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.4, "a": 0.28}],
    },
    {
        "key": "rotten",
        "task": "produce",
        "confident": True,
        "top": [
            {"label": "rotten_banana", "name": "Rotten banana", "prob": 0.92},
            {"label": "fresh_banana", "name": "Fresh banana", "prob": 0.05},
            {"label": "rotten_apple", "name": "Rotten apple", "prob": 0.02},
        ],
        "fruit": {"name": "Banana", "prob": 0.97},
        "state": {"name": "rotten", "prob": 0.92},
        "blobs": [
            {"x": 0.5, "y": 0.5, "r": 0.32, "a": 0.66},
            {"x": 0.7, "y": 0.36, "r": 0.15, "a": 0.42},
        ],
    },
    {
        "key": "lowconf",
        "task": "produce",
        "confident": False,
        "top": [
            {"label": "fresh_orange", "name": "Fresh orange", "prob": 0.46},
            {"label": "rotten_orange", "name": "Rotten orange", "prob": 0.31},
            {"label": "fresh_apple", "name": "Fresh apple", "prob": 0.12},
        ],
        "fruit": {"name": "Orange", "prob": 0.58},
        "state": {"name": "fresh", "prob": 0.6},
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.34, "a": 0.4}],
    },
    {
        "key": "fresh",
        "task": "produce",
        "confident": True,
        "top": [
            {"label": "fresh_apple", "name": "Fresh apple", "prob": 0.94},
            {"label": "fresh_orange", "name": "Fresh orange", "prob": 0.03},
            {"label": "rotten_apple", "name": "Rotten apple", "prob": 0.02},
        ],
        "fruit": {"name": "Apple", "prob": 0.96},
        "state": {"name": "fresh", "prob": 0.94},
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.4, "a": 0.28}],
    },
    {
        "key": "whitefly",
        "task": "pest",
        "confident": True,
        "top": [
            {"label": "Tomato_pest___Whitefly", "name": "Whitefly", "prob": 0.89},
            {"label": "Tomato_pest___Aphids", "name": "Aphids", "prob": 0.07},
            {"label": "Tomato_pest___No_pest", "name": "No pest detected", "prob": 0.03},
        ],
        "advice": "Whiteflies also spread tomato leaf curl virus. Use yellow sticky traps, protect nurseries with fine nets and remove heavily infested leaves. Ask your local agricultural extension office which products are registered for your area.",
        "blobs": [{"x": 0.46, "y": 0.42, "r": 0.26, "a": 0.68}, {"x": 0.68, "y": 0.64, "r": 0.16, "a": 0.5}],
    },
    {
        "key": "lowconf",
        "task": "pest",
        "confident": False,
        "top": [
            {"label": "Tomato_pest___Spider_mites", "name": "Spider mites", "prob": 0.38},
            {"label": "Tomato_pest___Thrips", "name": "Thrips", "prob": 0.31},
            {"label": "Tomato_pest___No_pest", "name": "No pest detected", "prob": 0.2},
        ],
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.34, "a": 0.42}],
    },
    {
        "key": "nopest",
        "task": "pest",
        "confident": True,
        "top": [
            {"label": "Tomato_pest___No_pest", "name": "No pest detected", "prob": 0.95},
            {"label": "Tomato_pest___Whitefly", "name": "Whitefly", "prob": 0.03},
            {"label": "Tomato_pest___Aphids", "name": "Aphids", "prob": 0.01},
        ],
        "blobs": [{"x": 0.5, "y": 0.5, "r": 0.4, "a": 0.26}],
    },
]

_cursor: dict[str, int] = {"leaf": 0, "produce": 0, "pest": 0}


def _forced() -> Optional[str]:
    return os.environ.get("FARMSIGHT_DEMO") or None


def pick_scenario(task: Task) -> Scenario:
    forced = _forced()
    pool = [s for s in SCENARIOS if s["task"] == task]
    hit = next((s for s in pool if s["key"] == forced), None) if forced else None
    if hit:
        return hit
    s = pool[_cursor[task] % len(pool)]
    _cursor[task] += 1
    return s


def _data_url(mime: str, data: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _render(file: UploadFile, blobs: list[Blob]) -> tuple[str, str]:
    """Return (photo, heatmap) data URLs. Uses Pillow if installed; otherwise both are the original image."""
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError:
        url = _data_url(file.type or "application/octet-stream", file.data)
        return url, url
    try:
        img = Image.open(io.BytesIO(file.data)).convert("RGB")
    except Exception:
        raise AnalyseError("unreadable")
    scale = min(1, 900 / max(img.width, img.height))
    w, h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    img = img.resize((w, h))

    def jpeg(im: Any) -> str:
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        return _data_url("image/jpeg", buf.getvalue())

    photo = jpeg(img)
    heat = img.convert("RGBA")
    stops = [(0.0, (228, 18, 18), 1.0), (0.2, (235, 80, 10), 0.9), (0.45, (242, 188, 18), 0.7),
             (0.7, (48, 210, 72), 0.38), (1.0, (18, 80, 210), 0.0)]
    for b in blobs:
        rad = b["r"] * min(w, h)
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        steps = max(1, int(rad))
        for i in range(steps, 0, -1):
            t = i / steps
            for (t0, c0, k0), (t1, c1, k1) in zip(stops, stops[1:]):
                if t <= t1:
                    f = (t - t0) / (t1 - t0)
                    col = tuple(round(c0[j] + (c1[j] - c0[j]) * f) for j in range(3))
                    alpha = round(255 * b["a"] * (k0 + (k1 - k0) * f))
                    break
            cx, cy, r = b["x"] * w, b["y"] * h, t * rad
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (alpha,))
        heat = Image.alpha_composite(heat, layer)
    return photo, jpeg(heat.convert("RGB"))


def demo_analyse(task: Task, file: UploadFile, delay: float = 2.2) -> AnalyseResult:
    forced = _forced()
    time.sleep(delay)
    if forced == "error":
        raise AnalyseError("server")
    if forced == "empty":
        raise AnalyseError("empty")

    sc = pick_scenario(task)
    photo, heatmap = _render(file, sc["blobs"])
    show_advice = sc["confident"] and bool(sc.get("advice"))
    return {
        "task": task,
        "confident": sc["confident"],
        "top": sc["top"],
        "fruit": sc.get("fruit"),
        "state": sc.get("state"),
        "advice": sc["advice"] if show_advice else None,
        "source": "Demo placeholder (no live knowledge source connected)" if show_advice else None,
        "disclaimer": "General guidance only. Please confirm with your local agricultural extension office.",
        "images": {"photo": photo, "heatmap": heatmap},
        "model_info": {"note": DEMO_NOTE},
    }
