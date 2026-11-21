"""Assemble a source-aware 14-crop leaf dataset without changing existing data."""

import argparse
import hashlib
import json
import random
import shutil
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image
from io import BytesIO


ROOT = Path(__file__).resolve().parents[2]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DISEASE_UNAVAILABLE = ["Carrot", "Orange", "Pomegranate"]
BANANA_URL = (
    "https://huggingface.co/datasets/Project-AgML/banana_leaf_disease_classification/"
    "resolve/main/data/train-00000-of-00001.parquet"
)
CUCUMBER_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/"
    "kaushigihanml/cucumber-leaf-disease-dataset?datasetVersionNumber=1"
)
BANANA_LABELS = {
    0: "healthy",
    1: "Sigatoka",
    2: "Xanthomonas",
}
CUCUMBER_LABELS = {
    "Downy_mildew": "Downy_mildew",
    "Healthy_leaves": "healthy",
    "Powdery_mildew": "Powdery_mildew",
}
ARCHIVE_CLASS_ALIASES = {
    "Tomato___Spider_mites Two-spotted_spider_mite": "Tomato___Spider_mites",
    "Tomato___Tomato_mosaic_virus": "Tomato___Mosaic_virus",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato___Yellow_Leaf_Curl_Virus",
}

# Images in this list have source and reuse metadata checked against Commons.
# These classes are crop-recognition only; they are not disease examples.
COMMONS_IMAGES = [
    {
        "crop": "Orange",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/81/Young_Orange_Tree_with_Green_Leaves_%28Citrus_%C3%97_sinensis%29.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Young_Orange_Tree_with_Green_Leaves_(Citrus_%C3%97_sinensis).jpg",
        "author": "Johnnybam",
        "license": "CC BY-SA 4.0",
        "group": "orange-healthy-tree",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/9/9e/Carrot-plant-leaves.JPG",
        "page": "https://commons.wikimedia.org/wiki/File:Carrot-plant-leaves.JPG",
        "author": "Edukeralam",
        "license": "CC BY-SA 3.0",
        "group": "carrot-seedling",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/73/Carrot_leaves.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Carrot_leaves.jpg",
        "author": "Kumar gyan prakash",
        "license": "CC BY-SA 4.0",
        "group": "carrot-leaves-india",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/44/Daucus_carota%27s_leaf.JPG",
        "page": "https://commons.wikimedia.org/wiki/File:Daucus_carota%27s_leaf.JPG",
        "author": "Imuzak",
        "license": "Public domain",
        "group": "carrot-leaf-pd",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0b/Daucus_carota_CloseupLeaves_SierraMadrona.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Daucus_carota_CloseupLeaves_SierraMadrona.jpg",
        "author": "Javier martin",
        "license": "Public domain",
        "group": "carrot-closeup",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/ea/Starr-090519-8068-Daucus_carota_subsp_sativus-leaves-Native_Nursery_Kula-Maui_%2824327125383%29.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Starr-090519-8068-Daucus_carota_subsp_sativus-leaves-Native_Nursery_Kula-Maui_(24327125383).jpg",
        "author": "Forest and Kim Starr",
        "license": "CC BY 3.0 US",
        "group": "carrot-starr-8068-8069",
    },
    {
        "crop": "Carrot",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3f/Starr-090519-8069-Daucus_carota_subsp_sativus-leaves-Native_Nursery_Kula-Maui_%2824927688096%29.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Starr-090519-8069-Daucus_carota_subsp_sativus-leaves-Native_Nursery_Kula-Maui_(24927688096).jpg",
        "author": "Forest and Kim Starr",
        "license": "CC BY 3.0 US",
        "group": "carrot-starr-8068-8069",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Pomegranate_leaf.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Pomegranate_leaf.jpg",
        "author": "CaNeCoRsO137",
        "license": "CC BY-SA 4.0",
        "group": "pomegranate-leaf-2023",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/37/Pomegranate_leaves.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Pomegranate_leaves.jpg",
        "author": "Mokkie",
        "license": "CC BY-SA 3.0",
        "group": "pomegranate-leaves-2014",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/5/54/Punicum_granatum_3.JPG",
        "page": "https://commons.wikimedia.org/wiki/File:Punicum_granatum_3.JPG",
        "author": "Dinkum",
        "license": "CC0",
        "group": "pomegranate-cc0",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/c9/PikiWiki_Israel_28682_Pomegranate_Branch.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:PikiWiki_Israel_28682_Pomegranate_Branch.jpg",
        "author": "Lehava Activity 2012 Pikiwiki Israel",
        "license": "CC BY 2.5",
        "group": "pomegranate-branch",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a6/Brot_de_fulles_de_magraner_IMGP0502.JPG",
        "page": "https://commons.wikimedia.org/wiki/File:Brot_de_fulles_de_magraner_IMGP0502.JPG",
        "author": "Aniol",
        "license": "CC BY-SA 3.0",
        "group": "pomegranate-sprouts",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Brot_de_fulles_de_magraner_IMGP0504.JPG",
        "page": "https://commons.wikimedia.org/wiki/File:Brot_de_fulles_de_magraner_IMGP0504.JPG",
        "author": "Aniol",
        "license": "CC BY-SA 3.0",
        "group": "pomegranate-sprouts",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/e/e4/Starr_030418-0026_Punica_granatum.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Starr_030418-0026_Punica_granatum.jpg",
        "author": "Forest and Kim Starr",
        "license": "CC BY 3.0",
        "group": "pomegranate-starr-2003",
    },
    {
        "crop": "Pomegranate",
        "url": "https://upload.wikimedia.org/wikipedia/commons/2/2a/Starr_080219-2960_Punica_granatum.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Starr_080219-2960_Punica_granatum.jpg",
        "author": "Forest and Kim Starr",
        "license": "CC BY 3.0",
        "group": "pomegranate-starr-2008",
    },
]


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "FarmSight/1.0 dataset preparation"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def image_files(folder):
    return sorted(
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def assign_group_splits(items, seed, label):
    fixed, movable = [], []
    for item in items:
        (fixed if item.get("split") else movable).append(item)
    if not movable:
        return fixed

    movable.sort(key=lambda item: item["key"])
    if len(movable) < 10:
        for item in movable:
            item["split"] = "train"
        return fixed + movable

    random.Random(f"{seed}:{label}").shuffle(movable)
    n_test = max(1, round(len(movable) * 0.15))
    n_validation = max(1, round(len(movable) * 0.15))
    if n_test + n_validation >= len(movable):
        n_validation = max(1, len(movable) - n_test - 1)
    for index, item in enumerate(movable):
        item["split"] = (
            "test" if index < n_test
            else "validation" if index < n_test + n_validation
            else "train"
        )
    return fixed + movable


def write_image(output, split, label, filename, contents):
    destination = output / split / label / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    destination.write_bytes(contents)


def add_grouped_records(output, records, seed, source):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["label"]].append(record)

    counts = Counter()
    archive_paths = {item["archive_path"] for item in records if "archive_path" in item}
    if len(archive_paths) > 1:
        raise ValueError(f"Expected one ZIP source for {source}")
    source_zip = zipfile.ZipFile(next(iter(archive_paths))) if archive_paths else None
    try:
        for label, items in grouped.items():
            for item in assign_group_splits(items, seed, label):
                split = item["split"]
                contents = item.get("contents")
                if contents is None:
                    contents = source_zip.read(item["archive_entry"])
                write_image(output, split, label, item["filename"], contents)
                counts[f"{split}/{label}"] += 1
    finally:
        if source_zip is not None:
            source_zip.close()
    return counts


def archive_records(archive_path, base_classes, base_images):
    records = []
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or Path(entry.filename).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            parts = entry.filename.split("/")
            if len(parts) < 3 or parts[0] != "disease":
                continue

            folder = parts[1]
            label = None
            if folder in base_classes or folder == "pomegranate":
                continue
            if folder == "Guava _Leaf" or folder == "jujube_Leaf":
                if len(parts) < 5 or parts[2] != "orginal":
                    continue
                crop = "Guava" if folder == "Guava _Leaf" else "Jujube"
                source_label = parts[3]
                if source_label.lower().startswith("healthy"):
                    disease = "healthy"
                elif source_label.lower().startswith("defect"):
                    disease = "Defect"
                else:
                    disease = source_label.replace(" ", "_")
                label = f"{crop}___{disease}"
            elif folder == "mango" and len(parts) >= 3:
                label = f"Mango___{parts[2].replace(' ', '_')}"
            elif folder.startswith("Pepper,_bell___"):
                label = folder.replace("Pepper,_bell___", "Bellpepper___", 1)
            elif folder.startswith("Orange___"):
                label = folder.replace("Haunglongbing", "Huanglongbing")
            elif "___" in folder:
                label = ARCHIVE_CLASS_ALIASES.get(folder, folder)

            if label is None:
                continue
            if (label, Path(entry.filename).name.lower()) in base_images:
                continue
            records.append({
                "label": label,
                "key": entry.filename,
                "filename": Path(entry.filename).name,
                "source_path": entry.filename,
                "archive_path": archive_path,
                "archive_entry": entry.filename,
            })
    return records


def banana_records(cache_dir):
    parquet = cache_dir / "banana_leaf_disease.parquet"
    if not parquet.exists():
        download(BANANA_URL, parquet)
    table = pq.read_table(parquet).to_pylist()
    records = []
    for row_index, row in enumerate(table):
        image = row["image"]
        contents = image.get("bytes")
        if contents is None:
            raise ValueError("Banana dataset record is missing embedded image bytes")
        disease = BANANA_LABELS[int(row["label"])]
        label = f"Banana___{disease}"
        records.append({
            "label": label,
            "key": f"banana-{row_index:05d}",
            "filename": f"banana_{row_index:05d}.jpg",
            "source_path": f"banana-parquet-row-{row_index}",
            "contents": contents,
        })
    return records


def cucumber_records(cache_dir):
    archive_path = cache_dir / "cucumber_leaf_disease_kaggle.zip"
    if not archive_path.exists():
        download(CUCUMBER_URL, archive_path)
    records = []
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or Path(entry.filename).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            parts = entry.filename.split("/")
            try:
                root_index = parts.index("cucumber_Leaf_Disease")
            except ValueError:
                continue
            if len(parts) < root_index + 4:
                continue
            source_split, class_name = parts[root_index + 1], parts[root_index + 2]
            if class_name not in CUCUMBER_LABELS:
                continue
            label = f"Cucumber___{CUCUMBER_LABELS[class_name]}"
            records.append({
                "label": label,
                "key": entry.filename,
                "filename": Path(entry.filename).name,
                "source_path": entry.filename,
                "archive_path": archive_path,
                "archive_entry": entry.filename,
                "split": "test" if source_split == "test" else None,
            })
    return records


def commons_records(cache_dir):
    records = []
    for index, metadata in enumerate(COMMONS_IMAGES):
        cache_path = cache_dir / "commons" / f"{metadata['group']}{Path(metadata['url']).suffix}"
        if cache_path.exists():
            contents = cache_path.read_bytes()
        else:
            contents = None
            last_error = None
            for attempt in range(5):
                try:
                    request = urllib.request.Request(
                        metadata["url"],
                        headers={
                            "User-Agent": (
                                "FarmSightDatasetPrep/1.0 "
                                "(https://commons.wikimedia.org/wiki/Commons:API_Usage_Policies)"
                            )
                        },
                    )
                    with urllib.request.urlopen(request, timeout=60) as response:
                        contents = response.read()
                    break
                except Exception as error:
                    last_error = error
                    if attempt < 4:
                        time.sleep(2 ** attempt)
            if contents is None:
                raise RuntimeError(f"Could not download Commons image {metadata['page']}") from last_error
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(contents)
        with Image.open(BytesIO(contents)) as image:
            image.verify()
        records.append({
            "label": f"{metadata['crop']}___leaf",
            "key": metadata["group"],
            "filename": f"{metadata['crop'].lower()}_commons_{index:02d}{Path(metadata['url']).suffix}",
            "source_path": metadata["page"],
            "contents": contents,
            "split": "train",
        })
    return records


def image_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as image:
        for block in iter(lambda: image.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def deduplicate_output(output, excluded_hashes=()):
    groups = defaultdict(list)
    records = []
    for split in ("train", "validation", "test"):
        split_dir = output / split
        if not split_dir.is_dir():
            continue
        for class_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
            for image in image_files(class_dir):
                records.append((split, class_dir.name, image))

    excluded_hashes = set(excluded_hashes)
    holdout_removed = 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        for digest, record in executor.map(lambda item: (image_digest(item[2]), item), records):
            if digest in excluded_hashes:
                record[2].unlink()
                holdout_removed += 1
                continue
            groups[digest].append(record)

    # Keep the evaluation copy so its matching training copy cannot leak into scoring.
    split_priority = {"test": 0, "validation": 1, "train": 2}
    removed = Counter()
    duplicate_groups = 0
    ambiguous_groups = 0
    for records in groups.values():
        if len(records) < 2:
            continue
        duplicate_groups += 1
        labels = {label for _, label, _ in records}
        if len(labels) > 1:
            ambiguous_groups += 1
            discarded = records
        else:
            keep = min(records, key=lambda item: (split_priority[item[0]], str(item[2])))
            discarded = [record for record in records if record != keep]
        for split, label, image in discarded:
            image.unlink()
            removed[f"{split}/{label}"] += 1

    counts = Counter()
    for split in ("train", "validation", "test"):
        split_dir = output / split
        if not split_dir.is_dir():
            continue
        for class_dir in split_dir.iterdir():
            if class_dir.is_dir():
                count = sum(1 for _ in image_files(class_dir))
                if not count:
                    class_dir.rmdir()
                    continue
                counts[f"{split}/{class_dir.name}"] = count
    return counts, {
        "duplicate_groups": duplicate_groups,
        "ambiguous_groups": ambiguous_groups,
        "removed_images": sum(removed.values()),
        "holdout_images_removed": holdout_removed,
    }


def copy_base_dataset(base, output):
    classes = set()
    base_images = set()
    counts = Counter()
    for split in ("train", "validation", "test"):
        split_dir = base / split
        if not split_dir.is_dir():
            raise FileNotFoundError(split_dir)
        for class_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
            classes.add(class_dir.name)
            for image in image_files(class_dir):
                target = output / split / class_dir.name / image.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    try:
                        target.hardlink_to(image)
                    except OSError:
                        shutil.copy2(image, target)
                counts[f"{split}/{class_dir.name}"] += 1
                base_images.add((class_dir.name, image.name.lower()))
    return classes, counts, base_images


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "disease.zip")
    parser.add_argument("--base", type=Path, default=ROOT / "data" / "leaf_mixed")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "leaf_all_crops")
    parser.add_argument("--cache", type=Path, default=ROOT / "data" / "external_leaf_sources")
    parser.add_argument("--holdout", type=Path, default=ROOT / "data" / "leaf_field_test")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    for required in (args.archive, args.base, args.holdout):
        if not required.exists():
            raise FileNotFoundError(required)
    if args.out.exists() and (args.out / "dataset_manifest.json").exists():
        raise SystemExit(f"Completed dataset already exists: {args.out}. Choose a fresh --out directory.")

    args.out.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    base_classes, counts, base_images = copy_base_dataset(args.base, args.out)

    for source_name, records in (
        ("disease.zip leaf-only classes", archive_records(args.archive, base_classes, base_images)),
        ("Project-AgML banana_leaf_disease_classification, CC BY 4.0", banana_records(args.cache)),
        ("Kaggle Cucumber Leaf Disease Dataset, Apache 2.0", cucumber_records(args.cache)),
        ("Wikimedia Commons leaf photographs; see per-image attribution", commons_records(args.cache)),
    ):
        counts.update(add_grouped_records(args.out, records, args.seed, source_name))
    holdout_hashes = {image_digest(image) for image in image_files(args.holdout)}
    counts, deduplication = deduplicate_output(args.out, holdout_hashes)

    sources = [
        {
            "name": "data/leaf_mixed",
            "license": "Existing local dataset; license not recorded in this repository",
        },
        {
            "name": "disease.zip",
            "license": "Archive license not recorded; imported labels restricted to verified leaf folders",
        },
        {
            "name": "Project-AgML/banana_leaf_disease_classification",
            "license": "CC BY 4.0",
            "url": "https://huggingface.co/datasets/Project-AgML/banana_leaf_disease_classification",
        },
        {
            "name": "Cucumber Leaf Disease Dataset by Kaushi Gihan",
            "license": "Apache 2.0",
            "url": "https://www.kaggle.com/datasets/kaushigihanml/cucumber-leaf-disease-dataset",
        },
        {
            "name": "Wikimedia Commons",
            "license": "Per-file license, author, source page, and URL are in commons_attribution",
        },
    ]
    classes = sorted({path.name for split in ("train", "validation", "test")
                      for path in (args.out / split).iterdir() if path.is_dir()})
    summary = {
        "seed": args.seed,
        "classes": classes,
        "class_crops": {label: label.split("___", maxsplit=1)[0] for label in classes},
        "disease_unavailable": DISEASE_UNAVAILABLE,
        "counts": dict(sorted(counts.items())),
        "deduplication": deduplication,
        "sources": sources,
        "commons_attribution": COMMONS_IMAGES,
    }
    (args.out / "dataset_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Dataset created: {args.out.resolve()}")
    print(f"Classes: {len(classes)} across {len(set(summary['class_crops'].values()))} crops")
    print("Disease diagnosis is unavailable for: " + ", ".join(DISEASE_UNAVAILABLE))
    print(
        "Duplicate-image cleanup: "
        f"{deduplication['duplicate_groups']} groups, "
        f"{deduplication['removed_images']} removed, "
        f"{deduplication['ambiguous_groups']} conflicting-label groups excluded"
    )
    print(f"Exact field-holdout duplicates excluded: {deduplication['holdout_images_removed']}")
    for key, count in sorted(counts.items()):
        print(f"{key:65s} {count:6d}")


if __name__ == "__main__":
    main()