"""Train a leaf/produce/other image gate from existing datasets and negative examples."""

import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms

CLASSES = ("leaf", "produce", "other")
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
IMAGE_EXTENSIONS = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


class GateDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]
        with Image.open(path) as image:
            image.seek(0)
            image = image.convert("RGB")
        return self.transform(image), label


def image_paths(root):
    return sorted(
        path for path in Path(root).rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def split_negative_images(paths, seed):
    shuffled = list(paths)
    random.Random(seed).shuffle(shuffled)
    if len(shuffled) < 3:
        raise ValueError("The negative-image folder must contain at least three images")
    test_count = max(1, round(len(shuffled) * 0.15))
    validation_count = max(1, round(len(shuffled) * 0.15))
    if test_count + validation_count >= len(shuffled):
        raise ValueError("The negative-image folder is too small for train/validation/test splits")
    return (
        shuffled[:len(shuffled) - validation_count - test_count],
        shuffled[len(shuffled) - validation_count - test_count:-test_count],
        shuffled[-test_count:],
    )


def collect_split(leaf_root, produce_root, negative_splits, split, seed, target_limit):
    rng = random.Random(seed + {"train": 0, "validation": 1, "test": 2}[split])
    samples = []
    for label, root in ((0, leaf_root), (1, produce_root)):
        paths = image_paths(Path(root) / split)
        if not paths:
            raise ValueError(f"No images found for {CLASSES[label]} in split {split}")
        if len(paths) > target_limit:
            paths = rng.sample(paths, target_limit)
        samples.extend((path, label) for path in paths)
    samples.extend((path, 2) for path in negative_splits[{"train": 0, "validation": 1, "test": 2}[split]])
    rng.shuffle(samples)
    return samples


def build_metrics(labels, predictions):
    confusion = np.zeros((len(CLASSES), len(CLASSES)), dtype=np.int64)
    for actual, predicted in zip(labels, predictions):
        confusion[actual, predicted] += 1
    recalls = [
        float(confusion[index, index] / max(confusion[index].sum(), 1))
        for index in range(len(CLASSES))
    ]
    return {
        "n_images": len(labels),
        "accuracy": float(np.trace(confusion) / max(confusion.sum(), 1)),
        "balanced_accuracy": float(np.mean(recalls)),
        "per_class_recall": dict(zip(CLASSES, recalls)),
        "confusion_matrix": confusion.tolist(),
    }


def run_epoch(model, loader, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    criterion = nn.CrossEntropyLoss()
    loss_total = 0.0
    labels, predictions = [], []
    for images, targets in loader:
        images, targets = images.to(device), targets.to(device)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, targets)
            if training:
                loss.backward()
                optimizer.step()
        loss_total += float(loss.detach()) * len(targets)
        labels.extend(targets.cpu().tolist())
        predictions.extend(logits.argmax(1).detach().cpu().tolist())
    return loss_total / len(loader.dataset), build_metrics(labels, predictions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--negative-images", required=True, type=Path)
    parser.add_argument("--leaf-data", type=Path, default=Path("data/leaf_all_crops_v5"))
    parser.add_argument("--produce-data", type=Path, default=Path("data/fruitveg"))
    parser.add_argument("--out", type=Path, default=Path("runs/input_gate"))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--target-limit", type=int, default=500)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--img", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.epochs < 1 or args.target_limit < 1 or args.batch < 1:
        parser.error("epochs, target-limit, and batch must be positive")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    negatives = image_paths(args.negative_images)
    if not negatives:
        parser.error(f"No supported images found in {args.negative_images}")
    negative_splits = split_negative_images(negatives, args.seed)
    splits = {
        split: collect_split(
            args.leaf_data, args.produce_data, negative_splits,
            split, args.seed, args.target_limit,
        )
        for split in ("train", "validation", "test")
    }

    eval_transform = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(args.img, scale=(0.65, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    train_dataset = GateDataset(splits["train"], train_transform)
    label_counts = np.bincount([label for _, label in splits["train"]], minlength=3)
    sample_weights = [
        1.0 / label_counts[label] for _, label in splits["train"]
    ]
    sampler = WeightedRandomSampler(
        sample_weights, num_samples=len(splits["train"]), replacement=True
    )
    train_loader = DataLoader(train_dataset, batch_size=args.batch, sampler=sampler)
    validation_loader = DataLoader(
        GateDataset(splits["validation"], eval_transform),
        batch_size=args.batch, shuffle=False,
    )
    test_loader = DataLoader(
        GateDataset(splits["test"], eval_transform),
        batch_size=args.batch, shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(model.last_channel, len(CLASSES))
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    args.out.mkdir(parents=True, exist_ok=True)

    best_balanced_accuracy = -1.0
    best_state = None
    started = time.time()
    for epoch in range(1, args.epochs + 1):
        train_loss, train_metrics = run_epoch(model, train_loader, device, optimizer)
        validation_loss, validation_metrics = run_epoch(model, validation_loader, device)
        score = validation_metrics["balanced_accuracy"]
        if score > best_balanced_accuracy:
            best_balanced_accuracy = score
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in model.state_dict().items()
            }
        print(
            f"Epoch {epoch}/{args.epochs}: "
            f"train loss={train_loss:.4f}, train balanced accuracy="
            f"{train_metrics['balanced_accuracy']:.3f}, validation loss="
            f"{validation_loss:.4f}, validation balanced accuracy={score:.3f}",
            flush=True,
        )

    if best_state is None:
        raise RuntimeError("Input-gate training did not produce a validation checkpoint")
    model.load_state_dict(best_state)
    _, test_metrics = run_epoch(model, test_loader, device)
    checkpoint = {
        "state_dict": best_state,
        "classes": list(CLASSES),
        "img": args.img,
        "arch": "mobilenet",
    }
    torch.save(checkpoint, args.out / "model.pt")
    report = {
        "classes": list(CLASSES),
        "train_images": len(splits["train"]),
        "validation_images": len(splits["validation"]),
        "test": test_metrics,
        "negative_images_total": len(negatives),
        "negative_images_by_split": {
            name: len(paths) for name, paths in zip(
                ("train", "validation", "test"), negative_splits
            )
        },
        "training_seconds": round(time.time() - started, 1),
        "validation_balanced_accuracy": best_balanced_accuracy,
        "threshold_note": (
            "This gate is trained only on the supplied negative-image distribution; "
            "performance on unseen out-of-domain image types is not guaranteed."
        ),
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
