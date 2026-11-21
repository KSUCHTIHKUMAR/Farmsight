"""FarmSight API. From the project root: ``uvicorn server:app --port 8000``."""

import base64
import importlib
import io
import json
import sys
import threading
import types
import warnings
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"
DIST = ROOT / "frontend" / "dist"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
CONF_OK = 0.60
DISCLAIMER = (
    "General guidance only. Consult your local agricultural extension office "
    "for the right product and dose."
)

# Reuse the Streamlit app's validated inference path so both interfaces load the
# same checkpoints and preserve preprocessing, class ordering, thresholds and CAMs.
if "app" not in sys.modules:
    app_package = types.ModuleType("app")
    app_package.__path__ = [str(APP_DIR)]
    sys.modules["app"] = app_package
sys.path.insert(0, str(APP_DIR))
original_app = importlib.import_module("app.app")

MODEL_FILES = {
    task: original_app.MODEL_FILES[task]
    for task in ("leaf", "leaf_specialist", "produce", "gate", "tomato_pest")
}
_lock = threading.Lock()

app = FastAPI(title="FarmSight API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8443",
        "http://127.0.0.1:8443",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode(
        "ascii"
    )


def _model_info(task: str) -> dict[str, Any]:
    if task == "leaf":
        metrics = original_app.load_leaf_metrics()
        return {
            "clean_accuracy": metrics.get("test_accuracy"),
            "field_accuracy": metrics.get("field_accuracy"),
            "note": (
                "Leaf predictions are suggestions, not confirmed diagnoses. "
                "The field-image evaluation covers only represented Potato and "
                "Tomato classes; other crop classes have not been independently "
                "validated on field photos."
            ),
        }
    if task == "produce":
        accuracy = original_app.PRODUCE_TEST_ACCURACY
        image_count = original_app.PRODUCE_TEST_IMAGES
        return {
            "clean_accuracy": accuracy,
            "field_accuracy": original_app.PRODUCE_FIELD,
            "note": (
                f"Scored {accuracy:.0%} on {image_count:,} held-out dataset images. "
                "Performance on real phone photos has not been measured."
            ),
        }

    metrics = original_app.load_pest_metrics()
    note = (
        f"The original tomato-pest model was evaluated on "
        f"{metrics.get('n_images', 0):,} held-out images with "
        f"{metrics.get('accuracy', 0):.0%} accuracy and "
        f"{metrics.get('macro_f1', 0):.0%} macro F1. "
        "Real-world field performance has not been independently validated."
        if metrics
        else "The tomato-pest model is experimental and has not been independently validated on field photos."
    )
    return {"note": note}


def _adapt_result(task: str, result: dict[str, Any]) -> dict[str, Any]:
    classes = result["classes"]
    probabilities = result["probs"]
    order = result["order"]
    top = []
    for index in order[:3]:
        label = classes[index]
        if task == "leaf":
            name = original_app.pretty(label)
        elif task == "produce":
            name = original_app.produce_guess(label)
        elif label == "Not_Tomato_Pest":
            name = "Not a supported tomato pest"
        else:
            name = f"Tomato pest category {label}"
        top.append({"label": label, "name": name, "prob": float(probabilities[index])})
    if not top:
        raise ValueError("The original inference returned no class predictions")

    response: dict[str, Any] = {
        "task": "pest" if task == "tomato_pest" else task,
        "top": top,
        "confident": False,
        "images": {
            "photo": _data_url(result["view"]),
            "heatmap": _data_url(result["overlay"]),
        },
        "model_info": _model_info(task),
    }

    if task == "leaf":
        crop_probability = float(result["crop_probability"])
        crop_supported = bool(result["crop_supported"])
        disease_supported = bool(result["disease_supported"])
        response.update(
            {
                "confident": (
                    crop_supported
                    and crop_probability >= CONF_OK
                    and (not disease_supported or top[0]["prob"] >= CONF_OK)
                ),
                "crop_probability": crop_probability,
                "crop_supported": crop_supported,
                "selected_crop": result["crop"],
                "disease_supported": disease_supported,
            }
        )
        if response["confident"] and disease_supported:
            treatment = original_app.load_treatments().get(top[0]["label"], {})
            response["advice"] = (
                treatment.get("advice")
                or "Guidance for this class has not been added yet."
            )
            response["source"] = treatment.get("source") or None
            response["disclaimer"] = DISCLAIMER
    elif task == "produce":
        produce_probability = float(result["produce_probability"])
        grade_probability = float(result["grade_probability"])
        response.update(
            {
                "confident": (
                    produce_probability >= CONF_OK
                    and grade_probability >= CONF_OK
                ),
                "fruit": {
                    "name": result["produce"],
                    "prob": produce_probability,
                },
                "state": {
                    "name": result["grade"],
                    "prob": grade_probability,
                },
            }
        )
    else:
        response.update(
            {
                "confident": bool(result["confident"]),
                "not_target": bool(result["not_target"]),
            }
        )

    return response


def analyse_image(task: str, image: Image.Image) -> dict[str, Any]:
    original_task = "tomato_pest" if task == "pest" else task
    if original_task not in {"leaf", "produce", "tomato_pest"}:
        raise ValueError(f"Unsupported analysis task: {task}")
    with _lock:
        result = original_app.analyse(original_task, image)
    return _adapt_result(original_task, result)


def _read_image(content: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as probe:
                if probe.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(
                        status_code=415,
                        detail="Use a JPEG, PNG, or WebP image.",
                    )
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=413,
                        detail="The image dimensions are too large to analyse.",
                    )
                probe.verify()
        return original_app.read_image(io.BytesIO(content))
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Couldn't read that image. Please try another photo.",
        ) from exc


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "models": {task: path.is_file() for task, path in MODEL_FILES.items()},
    }


@app.post("/api/analyse")
async def analyse(
    task: str = Form(...),
    file: UploadFile = File(...),
    crop: str | None = Form(None),
) -> dict[str, Any]:
    if task not in {"leaf", "produce", "pest", "tomato_pest"}:
        raise HTTPException(
            status_code=400,
            detail="task must be 'leaf', 'produce', or 'pest'",
        )
    if crop is not None:
        raise HTTPException(
            status_code=400,
            detail="Leaf crop is identified automatically; do not provide crop.",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="No image was uploaded.")

    image = _read_image(content)
    try:
        return analyse_image(task, image)
    except original_app.InvalidImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
