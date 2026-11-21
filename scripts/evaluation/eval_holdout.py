import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms
from sklearn.metrics import classification_report, confusion_matrix

from ..training.baseline_cnn import BaselineCNN, MEAN, STD, load_split, predict, save_confusion


def crop_aware_predictions(logits, true_labels, classes):
    crop_indices = {}
    for index, label in enumerate(classes):
        if "___" not in label:
            raise ValueError(f"Crop-aware evaluation requires Crop___Condition labels: {label}")
        crop = label.split("___", maxsplit=1)[0]
        crop_indices.setdefault(crop, []).append(index)

    predictions = []
    for row, target in zip(logits, true_labels):
        crop = classes[int(target)].split("___", maxsplit=1)[0]
        indices = crop_indices[crop]
        predictions.append(indices[int(row[indices].argmax())])
    return predictions


def build_model(ckpt):
    n = len(ckpt["classes"])
    if ckpt.get("arch") == "mobilenet":
        from torchvision import models
        m = models.mobilenet_v2(weights=None)
        m.classifier[1] = nn.Linear(m.last_channel, n)
    else:
        m = BaselineCNN(n)
    m.load_state_dict(ckpt["state_dict"])
    return m.eval()


def main():
    ap = argparse.ArgumentParser(description="Score a saved model on a real-world holdout folder (no retraining)")
    ap.add_argument("--run", required=True, help="Run folder with model.pt, e.g. runs\\leaf_baseline")
    ap.add_argument("--holdout", required=True, help="Holdout folder with one subfolder per class")
    ap.add_argument("--rotten_keyword", default=None, help="Ripeness only, e.g. rotten")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument(
        "--crop_aware",
        action="store_true",
        help="Restrict disease predictions to the crop in each holdout class label",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="Optional output directory for holdout metrics and plots (defaults to the run folder)",
    )
    args = ap.parse_args()

    run = Path(args.run)
    out_dir = Path(args.out) if args.out else run
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = torch.load(run / "model.pt", map_location="cpu")
    classes, img = ckpt["classes"], ckpt["img"]
    model = build_model(ckpt)

    tf = transforms.Compose([
        transforms.Resize((img, img)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    ds = load_split(Path(args.holdout), tf, args.rotten_keyword, ref_classes=classes)

    good, bad = [], 0
    for p, label in ds.samples:  # drop unreadable files instead of crashing
        try:
            with Image.open(p) as im:
                im.verify()
            good.append((p, label))
        except Exception:
            bad += 1
    ds.samples, ds.imgs, ds.targets = good, good, [l for _, l in good]
    if bad:
        print(f"Skipped {bad} unreadable files")
    if len(ds) == 0:
        print("No holdout images matched the model's class names. Check the subfolder names.")
        return

    loader = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)
    if args.crop_aware:
        y_true, y_pred = [], []
        with torch.no_grad():
            for images, labels in loader:
                logits = model(images)
                targets = labels.tolist()
                y_true.extend(targets)
                y_pred.extend(crop_aware_predictions(logits, targets, classes))
    else:
        y_true, y_pred = predict(model, loader, torch.device("cpu"))

    acc = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    acc = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    acc = sum(int(a == b) for a, b in zip(y_true, y_pred)) / len(y_true)
    present = sorted(set(y_true))
    names = [classes[i] for i in present]
    report_txt = classification_report(y_true, y_pred, labels=present, target_names=names, zero_division=0)
    report = classification_report(y_true, y_pred, labels=present, target_names=names,
                                   zero_division=0, output_dict=True)
    print(f"\n=== REAL-WORLD HOLDOUT ({len(y_true)} images, {len(present)} classes present) ===")
    print(report_txt)

    absent = [c for i, c in enumerate(classes) if i not in present]
    if absent:
        print("Classes with no holdout images (not scored):", ", ".join(absent))
    small = [f"{classes[i]} ({y_true.count(i)})" for i in present if y_true.count(i) < 10]
    if small:
        print("Too few images to trust (<10):", ", ".join(small))

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(classes))))

    result = {
        "n_images": len(y_true),
        "accuracy": acc,
        "macro_f1_present_classes": report["macro avg"]["f1-score"],
        "macro_recall_present_classes": report["macro avg"]["recall"],
        "per_class": {n: report[n] for n in names},
        "classes_not_scored": absent,
        "evaluation_mode": "crop-aware" if args.crop_aware else "global",
    }
    metrics_path = run / "metrics.json"
    if metrics_path.exists():
        clean = json.loads(metrics_path.read_text())["test"]["accuracy"]
        result["clean_test_accuracy"] = clean
        result["gap_points"] = round((clean - acc) * 100, 1)
        print(f"\nClean test accuracy: {clean:.3f}   Real-world accuracy: {acc:.3f}   "
              f"Gap: {result['gap_points']} points")
    (out_dir / "holdout_metrics.json").write_text(json.dumps(result, indent=2))
    save_confusion(cm, classes, out_dir / "confusion_holdout.png", f"Real-world holdout - {run.name}")
    print(f"Saved to {out_dir.resolve()}  (holdout_metrics.json, confusion_holdout.png)")


if __name__ == "__main__":
    main()
