import argparse
import json
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models, transforms
from sklearn.metrics import classification_report, confusion_matrix, f1_score

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .baseline_cnn import (
    BaselineCNN,
    MEAN,
    STD,
    carve_val,
    crop_class_names,
    filter_dataset_classes,
    load_split,
    predict,
    run_epoch,
    save_confusion,
)


def copy_checkpoint_weights(model, checkpoint, classes, architecture):
    checkpoint_classes = checkpoint.get("classes")
    if not isinstance(checkpoint_classes, list) or not checkpoint_classes:
        raise ValueError("Initialization checkpoint has no valid class mapping")
    checkpoint_arch = checkpoint.get("arch", "cnn")
    if checkpoint_arch != architecture:
        raise ValueError(
            f"Checkpoint architecture {checkpoint_arch!r} does not match "
            f"requested model {architecture!r}"
        )
    missing = set(checkpoint_classes) - set(classes)
    if missing:
        raise ValueError(
            "Expanded class mapping is missing checkpoint classes: "
            + ", ".join(sorted(missing))
        )

    head = "classifier.1" if architecture == "mobilenet" else "classifier.4"
    source_state = checkpoint["state_dict"]
    target_state = model.state_dict()
    for key, value in source_state.items():
        if key.startswith(f"{head}."):
            continue
        if key not in target_state or target_state[key].shape != value.shape:
            raise ValueError(f"Incompatible checkpoint tensor: {key}")
        target_state[key] = value
    model.load_state_dict(target_state)

    source_weight = source_state[f"{head}.weight"]
    source_bias = source_state[f"{head}.bias"]
    target_layer = model.classifier[1] if architecture == "mobilenet" else model.classifier[4]
    if source_weight.shape[1:] != target_layer.weight.shape[1:]:
        raise ValueError("Checkpoint classifier feature dimensions are incompatible")
    source_index = {label: index for index, label in enumerate(checkpoint_classes)}
    with torch.no_grad():
        for target_index, label in enumerate(classes):
            if label in source_index:
                source_row = source_index[label]
                target_layer.weight[target_index].copy_(source_weight[source_row])
                target_layer.bias[target_index].copy_(source_bias[source_row])


def build_model(name, num_classes, pretrained, checkpoint=None, classes=None):
    if name == "cnn":
        model = BaselineCNN(num_classes)
    else:
        weights = (
            models.MobileNet_V2_Weights.IMAGENET1K_V1
            if pretrained and checkpoint is None else None
        )
        model = models.mobilenet_v2(weights=weights)
        model.classifier[1] = nn.Linear(model.last_channel, num_classes)
    if checkpoint is not None:
        if classes is None:
            raise ValueError("Class names are required to load a checkpoint")
        copy_checkpoint_weights(model, checkpoint, classes, name)
    model.temperature = float(checkpoint.get("temperature", 2.0)) if checkpoint else 1.0
    return model


def evaluate_model(
    model, ds, args, device, out_dir, tag, title, model_classes=None
):
    loader = DataLoader(ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)
    raw_true, raw_pred = predict(model, loader, device)
    model_classes = list(model_classes or ds.classes)
    output_layer = model.classifier[-1] if isinstance(model, BaselineCNN) else model.classifier[1]
    if len(model_classes) != output_layer.out_features:
        raise ValueError("Model class mapping does not match its output layer")
    class_to_idx = {label: index for index, label in enumerate(ds.classes)}
    true_names = [ds.classes[index] for index in raw_true]
    predicted_names = [model_classes[index] for index in raw_pred]
    y_true = [class_to_idx[name] for name in true_names]
    unknown_index = len(ds.classes)
    y_pred = [class_to_idx.get(name, unknown_index) for name in predicted_names]
    labels = list(range(len(ds.classes)))
    txt = classification_report(
        y_true, y_pred, labels=labels, target_names=ds.classes, zero_division=0
    )
    rep = classification_report(
        y_true, y_pred, labels=labels, target_names=ds.classes,
        zero_division=0, output_dict=True,
    )
    unknown_predictions = sum(index == unknown_index for index in y_pred)
    confusion_labels = list(ds.classes)
    confusion_matrix_labels = labels
    if unknown_predictions:
        confusion_labels.append("Expanded-only class")
        confusion_matrix_labels = labels + [unknown_index]
    cm = confusion_matrix(y_true, y_pred, labels=confusion_matrix_labels)
    save_confusion(
        cm, confusion_labels, out_dir / f"confusion_{tag}.png",
        f"{title} - {tag}",
    )
    print(f"\n=== {tag.upper()} ({len(y_true)} images) ===")
    print(txt)
    (out_dir / f"classification_report_{tag}.txt").write_text(txt, encoding="utf-8")
    (out_dir / f"classification_report_{tag}.json").write_text(
        json.dumps(rep, indent=2), encoding="utf-8"
    )
    (out_dir / f"confusion_matrix_{tag}.json").write_text(
        json.dumps(cm.tolist()), encoding="utf-8"
    )
    return {
        "n_images": len(y_true),
        "accuracy": sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true),
        "predictions_into_expanded_only_classes": unknown_predictions,
        "macro_precision": rep["macro avg"]["precision"],
        "macro_recall": rep["macro avg"]["recall"],
        "macro_f1": rep["macro avg"]["f1-score"],
        "weighted_precision": rep["weighted avg"]["precision"],
        "weighted_recall": rep["weighted avg"]["recall"],
        "weighted_f1": rep["weighted avg"]["f1-score"],
        "per_class": {c: rep[c] for c in ds.classes},
    }


@torch.no_grad()
def calibrate_temperature(model, loader, device):
    model.eval()
    logits, labels = [], []
    for images, targets in loader:
        logits.append(model(images.to(device)).cpu())
        labels.append(targets.cpu())
    if not logits:
        raise ValueError("Validation split contains no images for calibration")
    all_logits = torch.cat(logits)
    all_labels = torch.cat(labels)
    log_temperature = torch.zeros((), requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=50)

    def closure():
        optimizer.zero_grad()
        temperature = log_temperature.exp().clamp(0.05, 20.0)
        loss = nn.functional.cross_entropy(all_logits / temperature, all_labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_temperature.detach().exp().clamp(0.05, 20.0))


def main():
    p = argparse.ArgumentParser(description="FarmSight Step 4/5: augmentation and MobileNetV2 transfer learning")
    p.add_argument("--data", required=True, help="Folder containing train/ val(or validation)/ test/")
    p.add_argument("--out", required=True, help="Where to save results")
    p.add_argument("--model", choices=["cnn", "mobilenet"], default="mobilenet")
    p.add_argument("--augment", action="store_true", help="Random crop/flip/rotation/color jitter on training images")
    p.add_argument("--no_pretrained", action="store_true", help="MobileNet from scratch (default: ImageNet weights)")
    p.add_argument("--class_weights", action="store_true", help="Weight the loss by inverse class frequency")
    p.add_argument("--rotten_keyword", default=None, help="Ripeness only, e.g. rotten")
    p.add_argument("--crops", default=None, help="Optional comma-separated crop names for Crop___Condition datasets")
    p.add_argument("--val_frac", type=float, default=0.15, help="Used only if there is no val/validation folder")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--img", type=int, default=128)
    p.add_argument("--lr", type=float, default=None, help="Default: 1e-3 for cnn, 3e-4 for mobilenet")
    p.add_argument("--workers", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--init_checkpoint",
        default=None,
        help="Existing checkpoint to fine-tune; compatible output rows are copied by class name",
    )
    p.add_argument(
        "--compare_checkpoint",
        default=None,
        help="Previous checkpoint to compare against on the same existing test images",
    )
    p.add_argument(
        "--compare_data",
        default=None,
        help="Dataset containing the prior checkpoint's test split",
    )
    p.add_argument("--early_stopping_patience", type=int, default=5)
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing model.pt only after successful training and evaluation",
    )
    args = p.parse_args()

    if args.epochs < 1 or args.early_stopping_patience < 1:
        p.error("epochs and early_stopping_patience must be positive")
    if bool(args.compare_checkpoint) != bool(args.compare_data):
        p.error("--compare_checkpoint and --compare_data must be specified together")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out)
    if (out_dir / "model.pt").exists() and not args.overwrite:
        p.error(
            f"{out_dir / 'model.pt'} already exists; choose a new --out or pass --overwrite"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    init_checkpoint = (
        torch.load(args.init_checkpoint, map_location="cpu", weights_only=False)
        if args.init_checkpoint else None
    )
    pretrained = (
        args.model == "mobilenet"
        and not args.no_pretrained
        and init_checkpoint is None
    )
    title = f"{args.model}{' +aug' if args.augment else ''}{' (pretrained)' if pretrained else ''}"
    print(f"Device: {device}   Run: {title}")

    norm = [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
    eval_tf = transforms.Compose([transforms.Resize((args.img, args.img))] + norm)
    if args.augment:
        train_tf = transforms.Compose([
            transforms.RandomResizedCrop(args.img, scale=(0.5, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(30),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
        ] + norm)
    else:
        train_tf = eval_tf

    data = Path(args.data)
    train_ds = load_split(data / "train", train_tf, args.rotten_keyword)
    classes = train_ds.classes
    if args.crops:
        selected_classes = crop_class_names(classes, args.crops.split(","))
        train_ds = filter_dataset_classes(train_ds, selected_classes)
        classes = train_ds.classes
    val_dir = next((data / n for n in ("val", "validation") if (data / n).exists()), None)
    if val_dir is not None:
        val_ds = load_split(val_dir, eval_tf, args.rotten_keyword, ref_classes=classes)
    else:
        print(f"No val/validation folder: holding out {args.val_frac:.0%} of train as validation.")
        val_ds = carve_val(train_ds, args.val_frac, args.seed)
        val_ds.transform = eval_tf  # validation images are never augmented
    test_ds = load_split(data / "test", eval_tf, args.rotten_keyword, ref_classes=classes)
    print(f"Classes ({len(classes)}): {classes}")
    print(f"train={len(train_ds)}  val={len(val_ds)}  test={len(test_ds)}")
    if not len(train_ds) or not len(val_ds) or not len(test_ds):
        raise ValueError("Training, validation, and test splits must all be non-empty")

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch, shuffle=False, num_workers=args.workers)

    model = build_model(
        args.model, len(classes), pretrained, init_checkpoint, classes
    ).to(device)
    n_params = sum(q.numel() for q in model.parameters())
    print(f"Parameters: {n_params:,}")

    weight = None
    if args.class_weights:
        counts = np.bincount(train_ds.targets, minlength=len(classes)).astype(float)
        w = np.sqrt(counts.sum() / (len(classes) * np.maximum(counts, 1)))
        w = np.clip(w, 0.25, 5.0)
        w /= w.mean()
        weight = torch.tensor(w, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight)
    lr = args.lr or (
        1e-4 if init_checkpoint else (3e-4 if args.model == "mobilenet" else 1e-3)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=2, min_lr=lr / 100
    )

    history = {
        "train_loss": [], "val_loss": [], "train_acc": [], "val_acc": [],
        "val_macro_f1": [], "learning_rate": [],
    }
    best_val_macro_f1, best_state, stale_epochs = -1.0, None, 0
    start = time.time()
    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, device)
        val_true, val_pred = predict(model, val_loader, device)
        val_macro_f1 = f1_score(
            val_true, val_pred, labels=list(range(len(classes))),
            average="macro", zero_division=0,
        )
        scheduler.step(va_loss)
        current_lr = optimizer.param_groups[0]["lr"]
        for key, value in (
            ("train_loss", tr_loss), ("val_loss", va_loss),
            ("train_acc", tr_acc), ("val_acc", va_acc),
            ("val_macro_f1", val_macro_f1), ("learning_rate", current_lr),
        ):
            history[key].append(value)
        if val_macro_f1 > best_val_macro_f1:
            best_val_macro_f1 = val_macro_f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
        print(
            f"Epoch {epoch:2d}/{args.epochs}  train loss {tr_loss:.4f} acc {tr_acc:.4f}  |  "
            f"val loss {va_loss:.4f} acc {va_acc:.4f} macro-F1 {val_macro_f1:.4f} "
            f"lr {current_lr:.2g}",
            flush=True,
        )
        if stale_epochs >= args.early_stopping_patience:
            print(f"Early stopping after {epoch} epochs without validation macro-F1 improvement.")
            break

    train_time = time.time() - start
    if best_state is None:
        raise RuntimeError("Training did not produce a validation checkpoint")
    print(
        f"\nTraining time: {train_time / 60:.1f} min  |  "
        f"best val macro-F1: {best_val_macro_f1:.4f}"
    )
    model.load_state_dict(best_state)
    model.temperature = calibrate_temperature(model, val_loader, device)
    print(f"Validation-calibrated temperature: {model.temperature:.3f}")

    results = {
        "classes": classes, "params": n_params, "train_time_sec": round(train_time, 1),
        "best_val_macro_f1": best_val_macro_f1,
        "temperature": model.temperature,
        "settings": {"model": args.model, "pretrained": pretrained, "augmentation": args.augment,
                     "class_weights": args.class_weights, "epochs": args.epochs, "batch": args.batch,
                     "img": args.img, "lr": lr, "seed": args.seed,
                     "early_stopping_patience": args.early_stopping_patience,
                     "init_checkpoint": args.init_checkpoint},
        "history": history,
    }
    results["validation"] = evaluate_model(
        model, val_ds, args, device, out_dir, "validation", title
    )
    results["test"] = evaluate_model(model, test_ds, args, device, out_dir, "test", title)
    if args.compare_checkpoint:
        prior_checkpoint = torch.load(
            args.compare_checkpoint, map_location="cpu", weights_only=False
        )
        prior_classes = prior_checkpoint.get("classes")
        if not prior_classes:
            raise ValueError("Comparison checkpoint has no class mapping")
        prior_test = load_split(
            Path(args.compare_data) / "test",
            eval_tf,
            args.rotten_keyword,
            ref_classes=prior_classes,
        )
        if not len(prior_test):
            raise ValueError("Comparison test split contains no matching images")
        prior_arch = prior_checkpoint.get("arch", "cnn")
        prior_model = build_model(
            prior_arch, len(prior_classes), False,
            prior_checkpoint, prior_classes,
        ).to(device)
        results["old_vs_new"] = {
            "evaluation": (
                "Same existing test images; predictions into expanded-only classes "
                "are counted as incorrect."
            ),
            "prior_checkpoint": args.compare_checkpoint,
            "prior": evaluate_model(
                prior_model, prior_test, args, device, out_dir,
                "comparison_prior", "Prior model", prior_classes,
            ),
            "expanded": evaluate_model(
                model, prior_test, args, device, out_dir,
                "comparison_expanded", "Expanded model", classes,
            ),
        }

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, name, key in ((axes[0], "Loss", "loss"), (axes[1], "Accuracy", "acc")):
        ax.plot(history[f"train_{key}"], label="train")
        ax.plot(history[f"val_{key}"], label="val")
        ax.set_title(f"{name} - {title}")
        ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "curves.png", dpi=150)
    plt.close(fig)

    checkpoint_path = out_dir / "model.pt"
    temporary_checkpoint = out_dir / "model.pt.tmp"
    torch.save(
        {
            "state_dict": best_state,
            "classes": classes,
            "img": args.img,
            "arch": args.model,
            "temperature": model.temperature,
        },
        temporary_checkpoint,
    )
    os.replace(temporary_checkpoint, checkpoint_path)
    with open(out_dir / "metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved results to {out_dir.resolve()}")
    print("Next: py eval_holdout.py --run " + str(out_dir) + " --holdout <real-world folder>")


if __name__ == "__main__":
    main()