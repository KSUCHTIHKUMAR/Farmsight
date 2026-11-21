# FarmSight leaf-model extension: integration and validation report

## Result

The app's leaf model now loads the expanded 59-class MobileNetV2 checkpoint at
`runs/leaf_extension_candidate/model.pt`. It retains the original 34 class
labels and compatible learned weights, and adds verified TOM2024 and Jute
classes. The previous seven-crop checkpoint remains at
`runs/leaf_7crop_candidate_v7/model.pt`. Produce grading remains separate and
continues to use its original 28-output checkpoint and 14-crop label mapping.

## Dataset audit and preparation

- The downloaded Jute dataset contains 900 images: 309 Cercospora Leaf Spot,
  327 Golden Mosaic, and 264 Healthy.
- TOM2024's English tree contains 12,230 images, with a similarly sized
  translated tree and 859 images in Category B. Duplicate translated content
  was not added as extra training data. Only reviewed leaf disease/pest
  categories were included; sampled non-leaf categories were excluded.
- The final prepared dataset has 42,526 training, 9,132 validation, and 9,063
  test images across 59 labels. Preparation removed 294 exact duplicates and
  28 conflicting-label duplicate groups. The audit found no exact overlap
  with the original base data or the existing 243-image field holdout.
- The split groups source-image families to prevent related images from
  crossing split boundaries. Training-only augmentation and class weighting
  are enabled.

See `data/leaf_all_crops_v6/dataset_manifest.json` and
`data/leaf_all_crops_v6/class_labels.json` for the detailed audit and mapping.

## Training and evaluation

The expanded model was fine-tuned from the preserved 34-class checkpoint for
five CPU epochs at 128x128 input resolution. Output rows were transferred by
class name; compatible feature weights were retained. Validation-based
temperature scaling selected 1.068. The test set was not used for tuning.

| Evaluation | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| Expanded model, 9,063-image independent test split | 95.92% | 88.74% | 95.92% |
| Original model, same 6,053-image comparison set | 98.60% | 98.41% | 98.61% |
| Expanded model, same 6,053-image comparison set | 98.55% | 98.61% | 98.56% |

Best validation macro F1 was 88.24% at epoch 4. On the existing 243-image
Potato/Tomato field holdout, crop-aware accuracy was 47.7% and macro F1 was
45.5%. The candidate therefore does not demonstrate strong field-photo
performance. The new Jute, Onion, and Maize classes have no independent field
holdout, and small classes have limited evidence. Results should not be
interpreted as field accuracy or guaranteed disease diagnoses.

## Integration and checks

- All 35 project tests passed.
- Updated Python modules passed `py_compile`.
- The expanded checkpoint loaded through the Streamlit model loader and the
  API's model loader; Grad-CAM generation and output shapes were checked.
- In-process API handler checks returned the existing health response shape,
  inferred a supported crop, rejected an unsupported crop with HTTP 400, and
  completed produce grading using the existing checkpoint.
- The production crop labels in `app/produce_labels.py` were not changed.
- The old seven-crop checkpoint remains available. The app uses the expanded
  checkpoint, while the specialist model is retained for compatible
  Potato/Tomato predictions.

The in-process checks do not substitute for a networked deployment test.
Unsupported-crop rejection covers the existing `Unknown` class and crop input
validation; it cannot guarantee rejection of every arbitrary image outside
the training distribution. Advice remains withheld unless confidence,
prediction stability, crop match, disease support, and field-validation gates
are all met.

## Generated outputs

- `classification_report_test.txt` and `classification_report_test.json`
- `confusion_test.png` and `confusion_matrix_test.json`
- `classification_report_comparison_prior.txt` and
  `classification_report_comparison_expanded.txt`
- `confusion_comparison_prior.png` and `confusion_comparison_expanded.png`
- `curves.png` and `gradcam.png`
- `field_eval/holdout_metrics.json` and `field_eval/confusion_holdout.png`
