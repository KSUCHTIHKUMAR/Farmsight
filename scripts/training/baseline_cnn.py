import argparse
import copy
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from sklearn.metrics import classification_report, confusion_matrix

import matplotlib
matplotlib.use("Agg")  # no display needed, just save files
import matplotlib.pyplot as plt

# Baseline CNN: no augmentation, no pretrained weights. It sets the floor that
# augmentation and MobileNetV2 must beat. Same ImageNet normalization as MobileNetV2 will need.
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


class BaselineCNN(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()

        def block(c_in, c_out):
            return nn.Sequential(
                nn.Conv2d(c_in, c_out, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )

        self.features = nn.Sequential(block(3, 32), block(32, 64), block(64, 128), block(128, 128))
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.pool(self.features(x)))


def load_split(path, tf, rotten_keyword=None, ref_classes=None):
    """
    Load an ImageFolder split.
    rotten_keyword: e.g. "rotten" -> binary: folders containing it become "rotten",
                    all other folders (apple, banana, orange) become "fresh".
    ref_classes:    force labels to follow this class list (for val/test/holdout).
    """
    ds = datasets.ImageFolder(path, transform=tf)
    folder_names = ds.classes

    if rotten_keyword:
        def to_name(folder):
            return "rotten" if rotten_keyword.lower() in folder.lower() else "fresh"
        classes = ["fresh", "rotten"]
    else:
        def to_name(folder):
            return folder
        classes = list(folder_names)

    if ref_classes is not None:
        classes = list(ref_classes)

    samples = []
    for p, idx in ds.samples:
        name = to_name(folder_names[idx])
        if name in classes:
            samples.append((p, classes.index(name)))

    ds.samples = samples
    ds.imgs = samples
    ds.targets = [s[1] for s in samples]
    ds.classes = classes
    ds.class_to_idx = {c: i for i, c in enumerate(classes)}
    return ds


def crop_class_names(classes, crops):
    """Return dataset classes belonging to the requested crop names."""
    selected_crops = {crop.strip().lower() for crop in crops if crop.strip()}
    if not selected_crops:
        raise ValueError("At least one crop name is required")
    matching = [
        label for label in classes
        if "___" in label and label.split("___", maxsplit=1)[0].lower() in selected_crops
    ]
    present_crops = {
        label.split("___", maxsplit=1)[0].lower()
        for label in matching
    }
    missing = selected_crops - present_crops
    if missing:
        raise ValueError(f"No dataset classes found for crops: {', '.join(sorted(missing))}")
    if not matching:
        raise ValueError("No crop-prefixed classes match the requested crops")
    return matching


def filter_dataset_classes(ds, selected_classes):
    """Filter and remap an ImageFolder dataset to a chosen class list."""
    selected_classes = list(selected_classes)
    if not selected_classes:
        raise ValueError("At least one dataset class is required")
    class_to_idx = {name: index for index, name in enumerate(selected_classes)}
    missing = set(selected_classes) - set(ds.classes)
    if missing:
        raise ValueError(f"Dataset classes are missing: {', '.join(sorted(missing))}")

    samples = [
        (path, class_to_idx[ds.classes[index]])
        for path, index in ds.samples
        if ds.classes[index] in class_to_idx
    ]
    if not samples:
        raise ValueError("No images remain after filtering dataset classes")
    ds.samples = samples
    ds.imgs = samples
    ds.targets = [label for _, label in samples]
    ds.classes = selected_classes
    ds.class_to_idx = class_to_idx
    return ds


def carve_val(train_ds, frac, seed):
    """No val folder? Hold out `frac` of each class from train (stratified) as validation."""
    rng = random.Random(seed)
    by_class = defaultdict(list)
    for s in train_ds.samples:
        by_class[s[1]].append(s)
    tr, va = [], []
    for items in by_class.values():
        rng.shuffle(items)
        k = max(1, int(len(items) * frac))
        va += items[:k]
        tr += items[k:]
    val_ds = copy.copy(train_ds)
    for ds, samples in ((train_ds, tr), (val_ds, va)):
        ds.samples = samples
        ds.imgs = samples
        ds.targets = [x[1] for x in samples]
    return val_ds


def run_epoch(model, loader, criterion, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss, correct, n = 0.0, 0, 0
    with torch.set_grad_enabled(training):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss = criterion(out, y)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * x.size(0)
            correct += (out.argmax(1) == y).sum().item()
            n += x.size(0)
    return total_loss / n, correct / n


@torch.no_grad()
def predict(model, loader, device):
    model.eval()
    y_true, y_pred = [], []
    for x, y in loader:
        out = model(x.to(device))
        y_true += y.tolist()
        y_pred += out.argmax(1).cpu().tolist()
    return y_true, y_pred


def save_confusion(cm, classes, path, title):
    k = len(classes)
    size = max(5, 0.6 * k)
    fig, ax = plt.subplots(figsize=(size, size))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(k))
    ax.set_yticks(range(k))
    ax.set_xticklabels(classes, rotation=90, fontsize=7)
    ax.set_yticklabels(classes, fontsize=7)
    for i in range(k):
        for j in range(k):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=6)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def evaluate(model, ds, args, device, out_dir, tag):
    loader = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)
    y_true, y_pred = predict(model, loader, device)
    labels = list(range(len(ds.classes)))
    report_txt = classification_report(
        y_true, y_pred, labels=labels, target_names=ds.classes, zero_division=0
    )
    report = classification_report(
        y_true, y_pred, labels=labels, target_names=ds.classes, zero_division=0, output_dict=True
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    save_confusion(cm, ds.classes, out_dir / f"confusion_{tag}.png", f"Baseline CNN - {tag}")
    print(f"\n=== {tag.upper()} ({len(y_true)} images) ===")
    print(report_txt)
    return {
        "n_images": len(y_true),
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "per_class": {c: report[c] for c in ds.classes},
    }


def main():
    p = argparse.ArgumentParser(description="Baseline CNN for FarmSight")
    p.add_argument("--data", required=True, help="Folder containing train/ val(or validation)/ test/")
    p.add_argument("--out", required=True, help="Where to save results")
    p.add_argument("--holdout", default=None, help="Optional real-world holdout folder (class subfolders)")
    p.add_argument("--rotten_keyword", default=None,
                   help='Binary mode, e.g. --rotten_keyword rotten: folders containing it '
                        'become "rotten", all others become "fresh"')
    p.add_argument("--val_frac", type=float, default=0.15,
                   help="Used only if there is no val/validation folder")
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--img", type=int, default=128, help="Images resized to img x img")
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--workers", type=int, default=2, help="Set 0 if DataLoader errors on Windows")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Device: {device}")

    # Baseline = NO augmentation: resize + normalize only.
    tf = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    data = Path(args.data)
    train_ds = load_split(data / "train", tf, args.rotten_keyword)
    classes = train_ds.classes
    val_dir = next((data / n for n in ("val", "validation") if (data / n).exists()), None)
    if val_dir is not None:
        val_ds = load_split(val_dir, tf, args.rotten_keyword, ref_classes=classes)
    else:
        print(f"No val/validation folder found: holding out {args.val_frac:.0%} of train as validation.")
        val_ds = carve_val(train_ds, args.val_frac, args.seed)
    test_ds = load_split(data / "test", tf, args.rotten_keyword, ref_classes=classes)
    print(f"Classes ({len(classes)}): {classes}")
    print(f"train={len(train_ds)}  val={len(val_ds)}  test={len(test_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)

    model = BaselineCNN(len(classes)).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Parameters: {n_params:,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
    best_val, best_state = -1.0, None
    start = time.time()

    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, device)
        for k, v in zip(history, (tr_loss, va_loss, tr_acc, va_acc)):
            history[k].append(v)
        if va_acc > best_val:  # model selection uses VAL only; test is touched once, at the end
            best_val = va_acc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        print(f"Epoch {epoch:2d}/{args.epochs}  train loss {tr_loss:.4f} acc {tr_acc:.4f}  |  "
              f"val loss {va_loss:.4f} acc {va_acc:.4f}")

    train_time = time.time() - start
    print(f"\nTraining time: {train_time / 60:.1f} min  |  best val acc: {best_val:.4f}")

    model.load_state_dict(best_state)

    results = {
        "classes": classes,
        "params": n_params,
        "train_time_sec": round(train_time, 1),
        "best_val_acc": best_val,
        "settings": {"epochs": args.epochs, "batch": args.batch, "img": args.img,
                     "lr": args.lr, "seed": args.seed, "augmentation": False},
        "history": history,
    }
    results["test"] = evaluate(model, test_ds, args, device, out_dir, "test")

    if args.holdout:
        hold_ds = load_split(Path(args.holdout), tf, args.rotten_keyword, ref_classes=classes)
        if len(hold_ds) == 0:
            print("\nHoldout skipped: no images matched the training class names.")
        else:
            results["holdout"] = evaluate(model, hold_ds, args, device, out_dir, "holdout")
            gap = results["test"]["accuracy"] - results["holdout"]["accuracy"]
            print(f"Clean-test vs real-world accuracy gap: {gap * 100:.1f} points")

    # Curves
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(history["train_loss"], label="train")
    axes[0].plot(history["val_loss"], label="val")
    axes[0].set_title("Loss")
    axes[0].legend()
    axes[1].plot(history["train_acc"], label="train")
    axes[1].plot(history["val_acc"], label="val")
    axes[1].set_title("Accuracy")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(out_dir / "curves.png", dpi=150)
    plt.close(fig)

    torch.save({"state_dict": best_state, "classes": classes, "img": args.img}, out_dir / "model.pt")
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {out_dir.resolve()}")


if __name__ == "__main__":
    main()