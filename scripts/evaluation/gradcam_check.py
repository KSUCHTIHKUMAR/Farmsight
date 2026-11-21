import argparse
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..training.baseline_cnn import BaselineCNN, MEAN, STD, load_split


def load_model(ckpt):
    classes = ckpt["classes"]
    if ckpt.get("arch") == "mobilenet":
        model = models.mobilenet_v2(weights=None)
        model.classifier[1] = nn.Linear(model.last_channel, len(classes))
    else:
        model = BaselineCNN(len(classes))
    model.load_state_dict(ckpt["state_dict"])
    return model


def gradcam(model, x):
    """Grad-CAM on the final feature block, explaining the model's predicted class."""
    acts, grads = [], []
    layer = model.features[-1]

    def fwd_hook(module, inp, out):
        _ = module, inp
        acts.append(out)
        out.register_hook(lambda g: grads.append(g))

    handle = layer.register_forward_hook(fwd_hook)
    out = model(x)
    handle.remove()

    pred = out.argmax(1).item()
    model.zero_grad()
    out[0, pred].backward()

    a, g = acts[0].detach(), grads[0].detach()
    weights = g.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * a).sum(dim=1, keepdim=True))
    cam = F.interpolate(cam, size=x.shape[2:], mode="bilinear", align_corners=False)[0, 0]
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    conf = out.softmax(1)[0, pred].item()
    return cam.numpy(), pred, conf


def short(name, width=24):
    name = name.replace("___", " ").replace("_", " ")
    return name if len(name) <= width else name[: width - 1] + "."


def main():
    ap = argparse.ArgumentParser(description="Grad-CAM sanity check for a saved baseline model")
    ap.add_argument("--run", required=True, help="Run folder containing model.pt, e.g. runs\\leaf_baseline")
    ap.add_argument("--data", required=True, help="Dataset folder containing the split, e.g. data\\leaf_disease")
    ap.add_argument("--split", default="test")
    ap.add_argument("--per_class", type=int, default=1, help="Images to sample per class")
    ap.add_argument("--rotten_keyword", default=None, help="Use for the ripeness model, e.g. rotten")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    ckpt = torch.load(Path(args.run) / "model.pt", map_location="cpu")
    classes, img = ckpt["classes"], ckpt["img"]
    model = load_model(ckpt)
    model.eval()
    for m in model.modules():  # in-place ReLU breaks gradient hooks
        if isinstance(m, nn.ReLU):
            m.inplace = False

    tf = transforms.Compose([
        transforms.Resize((img, img)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    ds = load_split(Path(args.data) / args.split, tf, args.rotten_keyword, ref_classes=classes)

    by_class = defaultdict(list)
    for path, label in ds.samples:
        by_class[label].append(path)
    rng = random.Random(args.seed)
    picks = []
    for label in range(len(classes)):
        paths = by_class.get(label, [])
        picks += [(p, label) for p in rng.sample(paths, min(args.per_class, len(paths)))]

    per_row = 3
    rows = (len(picks) + per_row - 1) // per_row
    fig, axes = plt.subplots(rows, per_row * 2, figsize=(per_row * 4.4, rows * 2.6))
    axes = np.atleast_2d(axes)
    for ax in axes.ravel():
        ax.axis("off")

    correct = 0
    for i, (path, label) in enumerate(picks):
        pil = Image.open(path).convert("RGB")
        x = tf(pil).unsqueeze(0)
        cam, pred, conf = gradcam(model, x)
        correct += int(pred == label)
        orig = np.asarray(pil.resize((img, img)))
        r, c = divmod(i, per_row)
        ax_o, ax_h = axes[r, c * 2], axes[r, c * 2 + 1]
        ax_o.imshow(orig)
        ax_h.imshow(orig)
        ax_h.imshow(cam, cmap="jet", alpha=0.45)
        ok = pred == label
        ax_o.set_title(f"true: {short(classes[label])}", fontsize=6.5)
        ax_h.set_title(f"pred: {short(classes[pred])} {conf:.0%}", fontsize=6.5,
                       color="green" if ok else "red")

    fig.tight_layout()
    out_path = Path(args.run) / "gradcam.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Sampled {len(picks)} images, {correct} predicted correctly.")
    print(f"Saved Grad-CAM grid to {out_path.resolve()}")


if __name__ == "__main__":
    main()