"""FarmSight - Streamlit app.   Run from the project folder:  streamlit run app/app.py"""
import base64
import html as _html
import json
from pathlib import Path

import matplotlib
import numpy as np
import streamlit as st
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageOps
from torchvision import models, transforms
from image_gate import task_image_confidence
from leaf_labels import (
    crop_has_disease_labels,
    infer_leaf_crop,
    rank_leaf_crops,
    should_use_potato_tomato_specialist,
)
from produce_labels import (
    PRODUCE_DISPLAY_NAMES,
    normalize_crop_name,
    produce_guess,
    summarize_produce,
)
from tomato_pest_labels import select_tomato_pest

ROOT = Path(__file__).parent
MODEL_FILES = {
    "leaf": ROOT.parent / "runs" / "leaf_expansion_candidate" / "model.pt",
    "leaf_specialist": ROOT / "models" / "leaf.pt",
    "produce": ROOT / "models" / "fruit.pt",
    "gate": ROOT.parent / "runs" / "input_gate" / "model.pt",
    "tomato_pest": ROOT.parent / "runs" / "tomato_pest_candidate" / "model.pt",
}
LEAF_METRICS_FILE = ROOT.parent / "runs" / "leaf_expansion_candidate" / "metrics.json"
PEST_METRICS_FILE = ROOT.parent / "runs" / "tomato_pest_candidate" / "metrics.json"
LEAF_FIELD_METRICS_FILE = (
    ROOT.parent / "runs" / "leaf_expansion_candidate" / "field_eval" / "holdout_metrics.json"
)
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
CONF_OK = 0.60  # Below this, request a better photo and withhold diagnosis advice.
IMAGE_GATE_CONFIDENCE = 0.70
TEMPERATURE = 1.0

# Numbers shown under "About this result".
LEAF_CLEAN, LEAF_FIELD = 0.9660209590346142, 0.51440329218107
PRODUCE_TEST_ACCURACY, PRODUCE_TEST_IMAGES = 0.9293515358361775, 2930
PRODUCE_FIELD = None  # Set after scoring real phone photos.

CSS = """
<style>
/* FarmSight theme and component styles */
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@600;800&family=Inter:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0');
:root {
  --forest: #24583f;
  --forest-deep: #183d2d;
  --ink: #20352a;
  --muted: #5a6b5f;
  --paper: #fbfaf6;
  --line: #e5e8dd;
}
html, body, .stApp, .stApp p, .stApp label { font-family: 'Inter', sans-serif; }
.stApp {
  background:
    radial-gradient(ellipse at 50% -18%, rgba(211, 230, 204, .55), transparent 48%),
    #f6f7f1;
  color: var(--ink);
}
header[data-testid="stHeader"], [data-testid="stToolbar"], footer, #MainMenu { visibility: hidden; height: 0; }
.block-container { max-width: 760px; padding: 2.4rem 1.5rem 4rem; }
h1, h2, h3 { font-family: 'Manrope', sans-serif; color: var(--ink); letter-spacing: -0.025em; }
h2 { font-size: clamp(1.55rem, 4vw, 2rem); margin: .45rem 0 .55rem; }
.stApp p { line-height: 1.65; }
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
  color: #4f6054 !important;
  opacity: 1 !important;
  line-height: 1.55;
}
div[role="radiogroup"] label,
div[role="radiogroup"] label p,
div[role="radiogroup"] label span { color: #1f2d24 !important; }
.stButton > button {
  width: 100%;
  min-height: 3rem;
  border: 1px solid #cbd9cd;
  border-radius: 14px;
  padding: .75rem 1rem;
  background: rgba(255, 255, 255, .88);
  box-shadow: 0 2px 7px rgba(28, 58, 39, .05);
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}
.stButton > button p { color: var(--forest); font-weight: 600; }
.stButton > button:hover {
  transform: translateY(-1px);
  border-color: var(--forest);
  box-shadow: 0 7px 18px rgba(28, 58, 39, .12);
}
.stButton > button:focus-visible { outline: 3px solid rgba(67, 129, 88, .3); outline-offset: 2px; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
  border-color: var(--forest);
  background: linear-gradient(135deg, #2f704f, var(--forest));
  box-shadow: 0 5px 14px rgba(36, 88, 63, .2);
}
.stButton > button[kind="primary"] p, .stButton > button[data-testid="stBaseButton-primary"] p {
  color: #fff;
  font-weight: 600;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
  background: linear-gradient(135deg, #286647, var(--forest-deep));
  box-shadow: 0 8px 19px rgba(36, 88, 63, .25);
}
.hero {
  position: relative;
  display: flex;
  min-height: 270px;
  flex-direction: column;
  justify-content: flex-end;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, .35);
  border-radius: 28px;
  padding: 34px clamp(24px, 5vw, 42px);
  color: #fff;
  margin-bottom: 22px;
  box-shadow: 0 18px 42px rgba(31, 77, 58, .18);
}
.hero h1 {
  max-width: 540px;
  color: #fff;
  font-size: clamp(2.15rem, 6vw, 3.25rem);
  line-height: 1.08;
  letter-spacing: -.045em;
  margin: 10px 0 0;
  text-wrap: balance;
}
.brand { font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 1.05rem; letter-spacing: .01em; }
.material-symbols-rounded { font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal; font-size: 1.2em; line-height: 1; vertical-align: -.18em; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 20px 0 24px; }
.dataset-section {
  margin: 24px 0 26px;
  padding: 19px;
  border: 1px solid var(--line);
  border-radius: 20px;
  background: rgba(255, 255, 255, .68);
  box-shadow: 0 8px 24px rgba(35, 57, 40, .045);
}
.dataset-section h2 { margin: 0 0 5px; font-size: 1.15rem; }
.dataset-intro { margin: 0 0 14px; color: var(--muted); font-size: .84rem; line-height: 1.5; }
.dataset-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 9px; }
.dataset-card {
  min-width: 0;
  min-height: 104px;
  padding: 12px 10px;
  border: 1px solid var(--line);
  border-top: 3px solid #67936c;
  border-radius: 13px;
  background: rgba(255, 255, 255, .92);
}
.dataset-card:nth-child(2) { border-top-color: #83a95c; }
.dataset-card:nth-child(3) { border-top-color: #a98651; }
.dataset-card:nth-child(4) { border-top-color: #b69045; }
.dataset-card:nth-child(5) { border-top-color: #597b9d; }
.dataset-name { color: var(--ink); font-size: .82rem; font-weight: 700; line-height: 1.3; overflow-wrap: anywhere; }
.dataset-kind { margin-top: 7px; color: var(--muted); font-size: .72rem; line-height: 1.4; }
.feature {
  min-height: 56px;
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, .82);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px 16px;
  font-size: .9rem;
  font-weight: 500;
  color: #34493b;
  box-shadow: 0 3px 10px rgba(35, 57, 40, .035);
}
.feature .material-symbols-rounded { color: var(--forest); margin-right: 9px; }
.task-card { padding: 0; margin: 0; border: 0; background: transparent; box-shadow: none; }
.task-card.leaf-card { background: transparent; border: 0; box-shadow: none; }
.st-key-leaf-task-card, .st-key-produce-task-card, .st-key-pest-task-card {
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 18px 20px 12px;
  margin: 10px 0 14px;
  background: rgba(255, 255, 255, .9);
  box-shadow: 0 5px 16px rgba(35, 57, 40, .045);
}
.st-key-leaf-task-card { border-left: 4px solid var(--forest); background: #f0f6ec; }
.st-key-pest-task-card { border-left: 4px solid #b27b32; background: #fbf5e9; }
.st-key-produce-task-card { border-left: 4px solid #66849a; background: #eef4f7; }
.st-key-leaf-task-card .stButton, .st-key-produce-task-card .stButton { margin-top: 10px; }
.card {
  background: rgba(255, 255, 255, .9);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 19px 21px;
  margin: 9px 0 12px;
  box-shadow: 0 5px 16px rgba(35, 57, 40, .045);
}
.card h3 { margin: 0 0 6px; font-size: 1.08rem; }
.card p { margin: 0; color: #5d6d62; font-size: .92rem; }
.leaf-card {
    background: #f0f6ec;
    border-color: #c8d9c2;
    border-left: 4px solid var(--forest);
    box-shadow: 0 8px 22px rgba(35, 77, 48, .08);
}
.leaf-card .chip { background: rgba(255, 255, 255, .82); }
.chip {
  display: inline-block;
  background: #f1f5ed;
  border: 1px solid #dce7d8;
  border-radius: 999px;
  padding: 4px 11px;
  font-size: .76rem;
  margin: 10px 6px 0 0;
  color: #355742;
}
.eyebrow { font-size: .72rem; letter-spacing: .12em; color: #6d8171; font-weight: 700; margin: 4px 0; }
.tip {
  background: #edf5e9;
  border: 1px solid #d8e8d2;
  color: #315c3e;
  border-radius: 14px;
  padding: .8rem 1rem;
  font-size: .87rem;
  margin: 12px 0 16px;
}
.leaf-tip { background: #e8f2e3; border-color: #cbdcc4; color: #28563a; }
.warn {
  background: #fff5e2;
  border: 1px solid #f1dfb8;
  color: #79500e;
  border-radius: 14px;
  padding: .8rem 1rem;
  font-size: .88rem;
  margin: 12px 0;
}
.big { font-family: 'Manrope', sans-serif; font-weight: 800; font-size: clamp(1.45rem, 4vw, 1.85rem); color: var(--ink); line-height: 1.2; }
.result-card { padding: 22px 23px; }
.result-card.positive { background: #eef5e9; border-color: #c3d6bd; border-left: 4px solid var(--forest); }
.result-card.caution { background: #fff8eb; border-color: #ecd9b3; border-left: 4px solid #b87816; }
.result-card .eyebrow { color: var(--forest); }
.result-card.caution .eyebrow { color: #79500e; }
.result-card .big { overflow-wrap: anywhere; }
.sub { color: var(--muted); font-size: .9rem; margin: 5px 0 10px; }
.bar-label { color: #4b5e50; font-size: .83rem; margin: 12px 0 5px; }
.reliability { display: inline-block; border-radius: 999px; padding: 3px 9px; margin-left: 5px; background: #fff1d6; border: 1px solid #ecd5a8; color: #79500e; font-size: .75rem; font-weight: 600; vertical-align: .1em; }
.bar-wrap { background: #e9ede4; border-radius: 999px; height: 9px; overflow: hidden; }
.bar { background: linear-gradient(90deg, #79a96f, var(--forest)); height: 9px; border-radius: 999px; }
.row { display: flex; justify-content: space-between; gap: 12px; font-size: .9rem; margin: 12px 0 5px; color: #354b3c; }
.small { font-size: .78rem; color: var(--muted); margin-top: 9px; line-height: 1.55; }
[data-testid="stFileUploader"] section {
  background: rgba(255, 255, 255, .74);
  border: 1px dashed #b8cbb9;
  border-radius: 16px;
}
[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
  color: #1f2d24 !important;
  background: #edf5e9 !important;
  border-color: #cbdcc4 !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *,
[data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"] {
  color: #1f2d24 !important;
  background-color: #edf5e9 !important;
  border-color: #cbdcc4 !important;
}
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 6px 18px rgba(25, 47, 32, .12); }
[data-testid="stExpander"] {
  border: 1px solid var(--line);
  border-radius: 15px;
  background: rgba(255, 255, 255, .72);
}
@media (max-width: 520px) {
  .block-container { padding: 1.25rem 1rem 3rem; }
  .hero { min-height: 230px; border-radius: 22px; padding: 26px 22px; }
  .grid2 { gap: 9px; }
  .feature { padding: 12px; font-size: .82rem; }
  .dataset-section { padding: 15px; }
  .dataset-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dataset-card { min-height: 88px; }
  .result-card { padding: 18px 17px; }
}
@media (min-width: 521px) and (max-width: 680px) {
  .dataset-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
"""


def md(s):
    st.markdown(s, unsafe_allow_html=True)


def esc(s):
    return _html.escape(str(s))


def pretty(label):
    t = label.replace("___", " — ").replace("_", " ")
    return t[:1].upper() + t[1:]


def go(page):
    st.session_state.page = page
    st.session_state._scroll_to_top = True
    st.rerun()


def back(page):
    c1, _ = st.columns([1, 3])
    with c1:
        if st.button("←  Back", key=f"back_to_{page}"):
            go(page)


def scroll_to_top():
    if st.session_state.pop("_scroll_to_top", False):
        st.html(
            "<script>window.parent.scrollTo({top: 0, behavior: 'instant'});</script>",
            width="content",
            unsafe_allow_javascript=True,
        )


def confidence_text(probability):
    return f"{min(float(probability), 0.99):.0%}"


# ---------------------------------------------------------------- model code
@st.cache_resource(show_spinner="Loading model...")
def load_model(path):
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    ckpt = torch.load(path, map_location="cpu")
    classes, size = ckpt["classes"], ckpt["img"]
    m = models.mobilenet_v2(weights=None)
    m.classifier[1] = nn.Linear(m.last_channel, len(classes))
    m.load_state_dict(ckpt["state_dict"])
    m.temperature = float(ckpt.get("temperature", TEMPERATURE))
    m.eval()
    return m, classes, size


def load_leaf_metrics():
    try:
        metrics = json.loads(LEAF_METRICS_FILE.read_text(encoding="utf-8"))
        field_metrics = json.loads(
            LEAF_FIELD_METRICS_FILE.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}
    test_metrics = metrics.get("test", {})
    field_accuracy = field_metrics.get("accuracy")
    return {
        "test_accuracy": test_metrics.get("accuracy"),
        "test_macro_f1": test_metrics.get("macro_f1"),
        "field_accuracy": field_accuracy,
        "field_accuracy_images": field_metrics.get("n_images"),
        "field_correct_predictions": round(
            float(field_accuracy) * int(field_metrics.get("n_images", 0))
        ) if field_accuracy is not None else None,
        "field_validated_classes": list(field_metrics.get("per_class", {})),
    }


def load_pest_metrics():
    try:
        return json.loads(PEST_METRICS_FILE.read_text(encoding="utf-8")).get(
            "test", {}
        )
    except (OSError, json.JSONDecodeError):
        return {}


def predict_with_cam(model, x, allowed_indices=None):
    """Class probabilities + Grad-CAM heatmap (for the predicted class) from the last conv block."""
    acts, grads = [], []

    def fwd(*hook_args):
        out = hook_args[-1]
        acts.append(out)
        out.register_hook(lambda g: grads.append(g))

    handle = model.features[-1].register_forward_hook(fwd)
    try:
        logits = model(x)
    finally:
        handle.remove()
    temperature = float(getattr(model, "temperature", TEMPERATURE))
    probs = (logits / temperature).softmax(1)[0].detach()
    if allowed_indices is None:
        top = int(probs.argmax())
    else:
        top = allowed_indices[int(logits[0, allowed_indices].argmax())]
    model.zero_grad()
    logits[0, top].backward()
    a, g = acts[0].detach(), grads[0].detach()
    weights = g.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * a).sum(dim=1, keepdim=True))
    cam = F.interpolate(cam, size=x.shape[2:], mode="bilinear", align_corners=False)[0, 0]
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    return probs.numpy(), cam.numpy()


class InvalidImageError(ValueError):
    """Raised when the model cannot confidently recognize the requested subject."""


def validate_image_type(task, img):
    if task == "tomato_pest":
        return
    gate, classes, size = load_model(MODEL_FILES["gate"])
    tf = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    x = tf(img).unsqueeze(0)
    with torch.no_grad():
        probabilities = gate(x).softmax(1)[0].tolist()
    confidence = task_image_confidence(task, classes, probabilities)
    if confidence < IMAGE_GATE_CONFIDENCE:
        subject = "a leaf" if task == "leaf" else "a fruit or vegetable"
        raise InvalidImageError(
            f"This image does not appear to resemble {subject}. "
            "Please upload a clear photo of the requested subject."
        )


def analyse(task, img):
    if task != "tomato_pest":
        validate_image_type(task, img)
    model, classes, size = load_model(MODEL_FILES[task])
    tf = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    x = tf(img).unsqueeze(0)
    leaf_crop = None
    leaf_indices = None
    crop_candidates = None
    if task == "leaf":
        with torch.no_grad():
            initial_probs = (
                model(x) / float(getattr(model, "temperature", TEMPERATURE))
            ).softmax(1)[0].numpy()
        crop_candidates = rank_leaf_crops(classes, initial_probs)[:2]
        top_label = classes[int(initial_probs.argmax())]
        top_crop = top_label.split("___", maxsplit=1)[0]
        specialist_classes = None
        if top_crop in {"Potato", "Tomato"}:
            specialist_classes = load_model(MODEL_FILES["leaf_specialist"])[1]
        if should_use_potato_tomato_specialist(
            classes, initial_probs, specialist_classes
        ):
            model, classes, specialist_size = load_model(
                MODEL_FILES["leaf_specialist"]
            )
            if specialist_size != size:
                tf = transforms.Compose([
                    transforms.Resize((specialist_size, specialist_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(MEAN, STD),
                ])
                x = tf(img).unsqueeze(0)
            size = specialist_size
            with torch.no_grad():
                initial_probs = (
                    model(x) / float(getattr(model, "temperature", TEMPERATURE))
                ).softmax(1)[0].numpy()
        leaf_crop, crop_probability, leaf_indices = infer_leaf_crop(
            classes, initial_probs
        )
        if not leaf_indices:
            raise ValueError(f"The leaf model has no labels for {leaf_crop}")
        with torch.enable_grad():
            probs, cam = predict_with_cam(model, x, leaf_indices)
    elif task == "tomato_pest":
        temperature = float(getattr(model, "temperature", TEMPERATURE))
        with torch.no_grad():
            view_logits = torch.stack(
                (model(x), model(x.flip(dims=(3,))))
            )
            view_probabilities = (view_logits / temperature).softmax(2)
            stable = bool(
                view_probabilities[0].argmax()
                == view_probabilities[1].argmax()
            )
            pest_probabilities = view_probabilities.mean(dim=0)[0].cpu().numpy()
            top_index = int(pest_probabilities.argmax())
        with torch.enable_grad():
            _, cam = predict_with_cam(model, x, [top_index])
        probs = pest_probabilities
    else:
        with torch.enable_grad():
            probs, cam = predict_with_cam(model, x)
        stable = True
    view = img.resize((320, 320))
    cam_img = Image.fromarray((cam * 255).astype(np.uint8)).resize((320, 320), Image.BILINEAR)
    heat = (matplotlib.colormaps["jet"](np.asarray(cam_img) / 255.0)[..., :3] * 255).astype(np.uint8)
    overlay = Image.blend(view, Image.fromarray(heat), 0.45)
    crop_probability = None
    disease_supported = None
    crop_supported = None
    if task == "leaf":
        crop = leaf_crop
        indices = leaf_indices
        crop_probability = float(probs[indices].sum())
        selected_probs = probs[indices] / max(crop_probability, 1e-8)
        order = [int(i) for i in np.argsort(-selected_probs)[:3]]
        result_classes = [classes[index] for index in indices]
        crop_supported = normalize_crop_name(crop) != "unknown"
        disease_supported = crop_supported and crop_has_disease_labels(classes, indices)
        if not disease_supported:
            order = order[:1]
        probs = selected_probs
        crop_display = PRODUCE_DISPLAY_NAMES.get(normalize_crop_name(crop), crop)
    elif task == "tomato_pest":
        pest_category, pest_confidence, not_target = select_tomato_pest(
            classes, probs, stable, CONF_OK
        )
        order = [int(i) for i in np.argsort(-probs)[:3]]
        if not_target:
            order = [int(np.argmax(probs))]
        result_classes = classes
    else:
        result_classes = classes
        order = [int(i) for i in np.argsort(-probs)[:3]]
    result = {
        "classes": result_classes,
        "probs": probs,
        "order": order,
        "view": view,
        "overlay": overlay,
    }
    if task == "leaf":
        result["crop"] = crop
        result["crop_display"] = crop_display
        result["crop_candidates"] = crop_candidates
        result["crop_probability"] = crop_probability
        result["crop_supported"] = crop_supported
        result["disease_supported"] = disease_supported
    if task == "produce":
        produce, produce_probability, grade, grade_probability = summarize_produce(classes, probs)
        if produce_probability < CONF_OK:
            raise InvalidImageError(
                "This image does not appear to resemble supported produce. "
                "Upload a clear photo of one fruit or vegetable."
            )
        result["produce"] = produce
        result["produce_probability"] = produce_probability
        result["grade"] = grade
        result["grade_probability"] = grade_probability
        result["produce_label"] = produce_guess(
            f"{produce.replace(' ', '')}__{'Rotten' if grade == 'rotten' else 'Healthy'}"
        )
    if task == "tomato_pest":
        result["pest_category"] = pest_category
        result["pest_confidence"] = pest_confidence
        result["not_target"] = not_target
        result["prediction_stable"] = stable
        result["confident"] = pest_category is not None or not_target
    return result


def read_image(file):
    img = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    img.thumbnail((1024, 1024))
    return img


def load_treatments():
    try:
        return json.loads((ROOT / "treatments.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def hero_style():
    p = ROOT / "assets" / "hero.jpg"
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode()
        return ("background-image: linear-gradient(rgba(20,50,35,.55), rgba(20,50,35,.85)), "
                f"url(data:image/jpeg;base64,{b64}); background-size: cover; background-position: center;")
    return "background: linear-gradient(135deg, #1F4D3A, #2D6A4F 60%, #4C9A72);"

# --------------------------------------------------------------------- pages
def landing():
    scroll_to_top()
    md(f'<div class="hero" style="{hero_style()}"><div class="brand"><span class="material-symbols-rounded">eco</span> FarmSight</div>'
       '<h1>Smarter crops start in the field.</h1></div>')
    st.write("Photograph a leaf or a piece of produce. FarmSight suggests likely diseases and checks "
             "freshness, with a heatmap showing what the AI looked at.")
    md('<div class="grid2"><div class="feature"><span class="material-symbols-rounded">eco</span>Leaf disease suggestions</div>'
       '<div class="feature"><span class="material-symbols-rounded">nutrition</span>Produce freshness check</div>'
       '<div class="feature"><span class="material-symbols-rounded">image_search</span>AI heatmap explanations</div>'
       '<div class="feature"><span class="material-symbols-rounded">lock</span>No account required</div></div>')
    md(
        '<section class="dataset-section">'
        '<h2>Built with five agricultural datasets</h2>'
        '<p class="dataset-intro">Leaf datasets share the crop-diagnosis model. '
        'Tomato insect pests use a separate classifier.</p>'
        '<div class="dataset-grid">'
        '<div class="dataset-card"><div class="dataset-name">TOM2024</div>'
        '<div class="dataset-kind">Tomato, onion, and maize leaves</div></div>'
        '<div class="dataset-card"><div class="dataset-name">Jute Leaf</div>'
        '<div class="dataset-kind">Healthy and disease categories</div></div>'
        '<div class="dataset-card"><div class="dataset-name">Groundnut Leaf</div>'
        '<div class="dataset-kind">Five verified leaf conditions</div></div>'
        '<div class="dataset-card"><div class="dataset-name">Turmeric Leaf</div>'
        '<div class="dataset-kind">Four source-labeled categories</div></div>'
        '<div class="dataset-card"><div class="dataset-name">Tomato Pests</div>'
        '<div class="dataset-kind">Eight pest categories · separate model</div></div>'
        '</div></section>'
    )
    if st.button("Get Started  →", type="primary", key="start"):
        go("task")

def card(icon, title, text, tags, class_name=""):
    chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in tags)
    md(f'<div class="task-card {class_name}"><h3>{icon} {esc(title)}</h3><p>{esc(text)}</p>{chips}</div>')

def task_page():
    scroll_to_top()
    back("landing")
    md('<div class="eyebrow">CHOOSE TASK</div>')
    st.markdown("## What are you analysing today?")
    st.caption("Each option runs a separate AI model tuned for that task.")
    with st.container(key="leaf-task-card"):
        card("🍃", "Diagnose Leaf",
            "Identify likely leaf conditions across 12 supported crops, including Groundnut, Jute, and Turmeric. Unsupported crops are not diagnosed.",
            ["12 supported crops", "Automatic crop ID"], class_name="leaf-card")
        if st.button("Diagnose Leaf  →", type="primary", key="pick_leaf"):
            st.session_state.task = "leaf"
            st.session_state.nonce += 1
            go("input")
    with st.container(key="pest-task-card"):
        card("🐛", "Identify Tomato Pests",
             "Classify eight tomato-pest image categories separately from leaf diseases. Uncertain and non-target images are rejected.",
             ["8 pest categories", "Separate classifier"])
        if st.button("Identify Tomato Pest  →", key="pick_tomato_pest"):
            st.session_state.task = "tomato_pest"
            st.session_state.nonce += 1
            go("input")
    with st.container(key="produce-task-card"):
        card("🍎", "Grade Produce",
             "Identify the produce and estimate whether it is fresh or rotten across 14 fruits and vegetables.",
             ["14 crops", "Fresh / Rotten"])
        if st.button("Grade Produce  →", key="pick_produce"):
            st.session_state.task = "produce"
            st.session_state.nonce += 1
            go("input")

def input_page():
    scroll_to_top()
    task = st.session_state.task
    leaf = task == "leaf"
    pest = task == "tomato_pest"
    n = st.session_state.nonce
    back("task")
    task_title = "DIAGNOSE LEAF" if leaf else (
        "IDENTIFY TOMATO PEST" if pest else "GRADE PRODUCE"
    )
    md(f'<div class="eyebrow">{task_title}</div>')
    st.markdown("## Add your photo")
    caption = (
        "Keep an affected leaf clear and close in the frame. Stems or branches may be visible, "
        "but disease estimates are based on leaf symptoms."
        if leaf
        else "Use a clear close-up of one insect. Pest categories are experimental and may not identify unrelated images."
        if pest else "Photograph the whole piece of fruit against a plain background."
    )
    st.caption(caption)
    tip_class = "tip leaf-tip" if leaf else "tip"
    md(f'<div class="{tip_class}">ℹ️ Best results: bright daylight, no blur, avoid heavy shadows on the subject.</div>')

    mode = st.radio("Photo source", ["Upload photo", "Take photo"], horizontal=True,
                    label_visibility="collapsed", key=f"mode_{n}")
    if mode == "Upload photo":
        file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"],
                                label_visibility="collapsed", key=f"up_{n}")
    else:
        file = st.camera_input("Take a photo", label_visibility="collapsed", key=f"cam_{n}")

    if file is None:
        return
    try:
        img = read_image(file)
    except Exception:
        st.error("Couldn't read that image. Please try another photo.")
        return
    _, preview, _ = st.columns([1, 2, 1])
    preview.image(img, width="stretch")
    if st.button("Analyse photo", type="primary", key=f"go_{n}"):
        with st.spinner("Analysing..."):
            try:
                st.session_state.result = analyse(task, img)
            except InvalidImageError as e:
                st.error(str(e))
                return
            except FileNotFoundError as e:
                st.error(str(e))
                return
            except Exception as e:
                st.error(f"Something went wrong while analysing the photo ({e}). Please try another photo.")
                return
        go("result")

def result_page():
    scroll_to_top()
    r = st.session_state.get("result")
    if r is None:
        go("landing")
        return
    leaf = st.session_state.task == "leaf"
    pest = st.session_state.task == "tomato_pest"
    classes, probs, order = r["classes"], r["probs"], r["order"]
    top = order[0]
    conf = float(probs[top])
    label = classes[top]
    if leaf:
        crop_probability = float(r["crop_probability"])
        crop_supported = bool(r.get("crop_supported", True))
        disease_supported = bool(r["disease_supported"])
        condition = label.split("___", maxsplit=1)[1]
        prediction_label = (
            f"{r['crop_display']} leaf" if crop_supported else "Unsupported leaf crop"
        )
        disease_label = f"Possible disease: {pretty(condition)}" if disease_supported else (
            "No diagnosis is available for this crop" if not crop_supported else
            "Disease prediction is unavailable for this crop"
        )
        metrics = load_leaf_metrics()
        field_accuracy = metrics.get("field_accuracy")
        field_validated = (
            field_accuracy is not None
            and label in metrics.get("field_validated_classes", [])
            and float(field_accuracy) >= CONF_OK
        )
        confident = (
            crop_supported
            and crop_probability >= CONF_OK
            and (not disease_supported or conf >= CONF_OK)
        )
        confidence_details = f"Crop identification: {confidence_text(crop_probability)}"
        confidence_bar = crop_probability
    elif pest:
        pest_category = r["pest_category"]
        not_target = bool(r["not_target"])
        confident = bool(r["confident"])
        prediction_label = (
            f"Tomato pest category {pest_category}"
            if pest_category else
            "Not a supported tomato pest" if not_target else
            "Pest category uncertain"
        )
        disease_label = (
            "No pest category identified" if not_target else
            "Possible insect category" if pest_category else
            "No pest diagnosis returned"
        )
        confidence_details = (
            f"Category confidence: {confidence_text(r['pest_confidence'])}"
        )
        confidence_bar = float(r["pest_confidence"])
        confidence_bar_label = "Pest-category confidence"
    else:
        produce_probability = float(r["produce_probability"])
        grade_probability = float(r["grade_probability"])
        prediction_label = r["produce_label"]
        disease_label = f"Condition: {r['grade'].title()}"
        confident = produce_probability >= CONF_OK and grade_probability >= CONF_OK
        confidence_details = (
            f"Fruit identification: {confidence_text(produce_probability)}"
        )
        confidence_bar = grade_probability
        confidence_bar_label = "Freshness estimate"

    back("input")
    positive_result = (
        "healthy" in condition.lower()
        if leaf else
        False if pest
        else r["grade"].lower() in {"healthy", "fresh"}
    )
    result_class = "card result-card positive" if positive_result else "card result-card caution"
    result_heading = (
        "UNSUPPORTED LEAF CROP"
        if leaf and not crop_supported else
        "LEAF CROP AND DISEASE · CROP UNCERTAIN"
        if leaf and r["disease_supported"] and float(r["crop_probability"]) < CONF_OK else
        "LEAF CROP AND POSSIBLE DISEASE" if leaf and r["disease_supported"] else
        "LEAF CROP" if leaf else
        "TOMATO PEST CATEGORY" if pest else
        "LIKELY PRODUCE AND CONDITION"
    )
    disease_badge = (
        '<span class="reliability">Experimental field validation</span>'
        if leaf and disease_supported and field_validated
        else ""
    )
    bar_value = min(float(confidence_bar), 0.99)
    bar_label = (
        "Crop identification" if leaf else
        confidence_bar_label
    )
    md(f'<div class="{result_class}"><div class="eyebrow">{result_heading}</div>'
       f'<div class="big">{esc(prediction_label)}</div>'
       f'<div class="sub">{esc(disease_label)}{disease_badge if disease_badge else ""}</div>'
       f'<div class="bar-label">{esc(confidence_details if leaf else bar_label + ": " + confidence_text(bar_value))}</div>'
       f'<div class="bar-wrap"><div class="bar" style="width:{bar_value * 100:.0f}%"></div></div></div>')
    if not confident:
        if leaf:
            if not crop_supported:
                warning = (
                    "⚠️ This leaf does not match a supported crop. No disease or pest "
                    "diagnosis is provided."
                )
            elif (
                r["disease_supported"]
                and not field_validated
                and crop_probability >= CONF_OK
                and conf >= CONF_OK
            ):
                warning = (
                    "⚠️ This crop does not have an independent field test set yet. "
                    "Treat the disease estimate as experimental and confirm locally."
                )
            elif r["disease_supported"] and not field_validated:
                field_classes = metrics.get("field_validated_classes", [])
                if label not in field_classes:
                    warning = (
                        "⚠️ This class has no independent field-photo test set. "
                        "Treat the estimate as experimental and confirm locally."
                    )
                else:
                    field_accuracy_text = (
                        f"only {int(metrics.get('field_correct_predictions', 0))} of "
                        f"{int(metrics.get('field_accuracy_images', 0))} field images "
                        f"({float(field_accuracy):.0%})"
                        if field_accuracy is not None
                        else "not independently validated on real-world field photos"
                    )
                    warning = (
                        f"⚠️ Disease suggestions are experimental: {field_accuracy_text} "
                        "had matching crop and disease labels. Confirm with a local expert; "
                        "treatment advice is withheld."
                    )
            else:
                warning = "⚠️ The disease estimate is uncertain. Try a clearer close-up and confirm the result locally."
        elif pest:
            warning = (
                "⚠️ This image was classified as outside the supported tomato-pest "
                "categories. No pest diagnosis is provided."
                if not_target else
                "⚠️ The tomato-pest category is uncertain. Try a clear close-up of "
                "one insect; no pest diagnosis is provided."
            )
        else:
            warning = (
                "⚠️ I am not confident in both the produce and freshness estimate. "
                "Try a clear, close photo of one item against a plain background."
            )
        md(f'<div class="warn">{warning}</div>')
    if leaf and crop_probability < CONF_OK:
        if len(r["crop_candidates"]) > 1:
            first_crop, first_score = r["crop_candidates"][0]
            second_crop, second_score = r["crop_candidates"][1]
            first_name = PRODUCE_DISPLAY_NAMES.get(
                normalize_crop_name(first_crop), first_crop
            )
            second_name = PRODUCE_DISPLAY_NAMES.get(
                normalize_crop_name(second_crop), second_crop
            )
            crop_warning = (
                f"⚠️ Crop is uncertain. Leading possibilities: {esc(first_name)} "
                f"({confidence_text(first_score)}) or {esc(second_name)} "
                f"({confidence_text(second_score)}). "
                "Try a closer, sharper photo showing one leaf."
            )
        else:
            crop_warning = (
                "⚠️ Crop identification is uncertain. Try a closer, sharper photo "
                "showing one leaf."
            )
        md(f'<div class="warn">{crop_warning}</div>')
    if leaf and not r["disease_supported"]:
        md('<div class="tip leaf-tip">Disease diagnosis is not available for this crop yet. '
           'This result identifies the leaf only. Crop recognition has limited examples and has '
           'not been independently validated for this crop.</div>')

    if not (pest and r["not_target"]):
        md('<div class="eyebrow">TOP GUESSES</div>')
        visible_guesses = [i for i in order if float(probs[i]) >= 0.01]
        if conf > 0.90:
            visible_guesses = visible_guesses[:2]
        for i in visible_guesses:
            guess = (
                f"{r['crop_display']} leaf · "
                f"{pretty(classes[i].split('___', maxsplit=1)[1])}"
                if leaf and r["disease_supported"]
                else f"{r['crop_display']} leaf" if leaf
                else f"Tomato pest category {classes[i]}" if pest
                else produce_guess(classes[i])
            )
            guess_probability = min(float(probs[i]), 0.99)
            md(f'<div class="row"><span>{esc(guess)}</span><span>{confidence_text(guess_probability)}</span></div>'
               f'<div class="bar-wrap"><div class="bar" style="width:{guess_probability * 100:.0f}%"></div></div>')

    md('<div class="eyebrow" style="margin-top:18px">WHAT THE MODEL LOOKED AT</div>')
    c1, c2 = st.columns(2)
    c1.image(r["view"], caption="Your photo", width="stretch")
    c2.image(r["overlay"], caption="Heatmap", width="stretch")
    st.caption("Red/yellow areas influenced the prediction most. The heatmap is coarse and shows influence, not proof.")

    if leaf and r["disease_supported"]:
        if confident:
            t = load_treatments().get(label, {})
            advice = t.get("advice") or "Guidance for this class has not been added yet."
            src = f'<div class="small">Source: {esc(t["source"])}</div>' if t.get("source") else ""
            md(f'<div class="card"><h3>🌱 Suggested next steps</h3><p>{esc(advice)}</p>{src}'
               '<div class="small">General guidance only. Consult your local agricultural extension office '
               'for the right product and dose.</div></div>')
        elif pest:
            pest_metrics = load_pest_metrics()
            if pest_metrics:
                st.write(
                    f"This model was evaluated on {pest_metrics.get('n_images', 0):,} "
                    f"held-out images with {pest_metrics.get('accuracy', 0):.0%} "
                    f"accuracy and {pest_metrics.get('macro_f1', 0):.0%} macro F1. "
                    "The evaluation uses the downloaded dataset and represented "
                    "non-target images; real-world field performance has not been "
                    "independently validated."
                )
            else:
                st.write(
                    "This separate tomato-pest classifier is experimental. "
                    "Real-world field performance has not been independently validated."
                )
            st.caption(
                "The downloaded folders use abbreviated pest labels; FarmSight "
                "does not infer species names absent from the source labels."
            )
        else:
            md('<div class="small">Treatment guidance is only shown for confident predictions.</div>')

    with st.expander("About this result"):
        if leaf:
            metrics = load_leaf_metrics()
            clean = metrics.get("test_accuracy")
            field = metrics.get("field_accuracy")
            details = []
            if clean is not None:
                details.append(f"overall held-out accuracy {float(clean):.0%}")
            if field is not None:
                details.append(
                    f"crop-aware accuracy on the existing potato/tomato field set "
                    f"{float(field):.0%}"
                )
            summary = "; ".join(details) if details else "performance varies by crop and photo conditions"
            st.write(
                f"This model has {summary}. Treat predictions as a suggestion, not a diagnosis. "
                "The field set does not include the new Groundnut, Turmeric, Maize, "
                "Onion, or Jute classes, and "
                "performance varies by crop and photo conditions. Confirm important decisions "
                "with a local agricultural expert."
            )
        else:
            st.write(
                f"This model scored {PRODUCE_TEST_ACCURACY:.0%} on "
                f"{PRODUCE_TEST_IMAGES:,} held-out dataset images. "
                "Performance on real phone photos has not been measured."
                + (f" On our own phone photos it scored {PRODUCE_FIELD:.0%}."
                   if PRODUCE_FIELD is not None else "")
            )

    if st.button("Analyse another photo", type="primary", key="again"):
        st.session_state.result = None
        st.session_state.nonce += 1
        go("input")
    if st.button("Start over", key="restart"):
        go("landing")

# ---------------------------------------------------------------------- main
if __name__ == "__main__":
    st.set_page_config(page_title="FarmSight", page_icon="🌿", layout="centered")
    md(CSS)
    for key, value in {"page": "landing", "task": None, "nonce": 0, "result": None}.items():
        st.session_state.setdefault(key, value)

    {"landing": landing, "task": task_page, "input": input_page, "result": result_page}[st.session_state.page]()