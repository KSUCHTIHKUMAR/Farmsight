import unittest
import importlib.util
import importlib
import sys
import types
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))
APP_PACKAGE = types.ModuleType("app")
APP_PACKAGE.__path__ = [str(APP_DIR)]
sys.modules["app"] = APP_PACKAGE
streamlit_app = importlib.import_module("app.app")
MODEL_FILES = streamlit_app.MODEL_FILES
load_model = streamlit_app.load_model
predict_with_cam = streamlit_app.predict_with_cam
from app.leaf_labels import (
    crop_has_disease_labels,
    infer_leaf_crop,
    should_use_potato_tomato_specialist,
)
from app.model_inference import predict_with_cam as predict_with_flip_cam
from app.produce_labels import PRODUCE_DISPLAY_NAMES, produce_guess
import server
ROOT = Path(__file__).resolve().parents[1]


class ModelLoadingTests(unittest.TestCase):
    def test_expanded_checkpoint_loads_for_streamlit_and_gradcam(self):
        model, classes, image_size = load_model(MODEL_FILES["leaf"])
        self.addCleanup(streamlit_app.load_model.clear)

        self.assertEqual(len(classes), 68)
        self.assertEqual(image_size, 128)
        self.assertAlmostEqual(model.temperature, 1.0418366193771362, places=4)
        self.assertIn("Jute___Cercospora_Leaf_Spot", classes)
        self.assertIn("Maize___Stripe", classes)
        self.assertIn("Onion___Caterpillar", classes)
        self.assertIn("Groundnut___Rosette", classes)
        self.assertIn("Turmeric___Leaf_Spot", classes)

        for module in model.modules():
            if isinstance(module, nn.ReLU):
                module.inplace = False
        probabilities, cam = predict_with_cam(model, torch.rand(1, 3, 128, 128))
        self.assertEqual(probabilities.shape, (len(classes),))
        self.assertEqual(cam.shape, (128, 128))
        self.assertTrue(torch.isfinite(torch.from_numpy(probabilities)).all())
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=5)

    def test_specialist_does_not_override_new_tomato_labels(self):
        model, classes, _ = load_model(MODEL_FILES["leaf"])
        specialist, specialist_classes, _ = load_model(
            MODEL_FILES["leaf_specialist"]
        )
        self.addCleanup(streamlit_app.load_model.clear)
        del model, specialist

        self.assertFalse(
            should_use_potato_tomato_specialist(
                classes,
                [1.0 if label == "Tomato___Alternaria" else 0.0 for label in classes],
                specialist_classes,
            )
        )

    def test_unknown_crop_maps_to_no_disease_advice(self):
        crop, probability, indices = infer_leaf_crop(
            ["Unknown___leaf", "Tomato___healthy"], [0.8, 0.2]
        )
        self.assertEqual(crop, "Unknown")
        self.assertGreater(probability, 0.7)
        self.assertFalse(crop_has_disease_labels(["Unknown___leaf"], indices))

    def test_gradcam_inference_temperature_and_produce_labels_stay_compatible(self):
        checkpoint = torch.load(
            MODEL_FILES["produce"], map_location="cpu", weights_only=False
        )
        model = models.mobilenet_v2(weights=None)
        model.classifier[1] = nn.Linear(model.last_channel, len(checkpoint["classes"]))
        model.load_state_dict(checkpoint["state_dict"])
        model.temperature = float(checkpoint.get("temperature", 1.0))
        model.eval()
        probabilities, cam, stable, crop_probability = predict_with_flip_cam(
            model, torch.rand(1, 3, checkpoint["img"], checkpoint["img"])
        )

        self.assertEqual(len(checkpoint["classes"]), 28)
        self.assertEqual(probabilities.shape, (28,))
        self.assertEqual(cam.shape, (checkpoint["img"], checkpoint["img"]))
        self.assertIsInstance(stable, bool)
        self.assertEqual(crop_probability, 1.0)
        self.assertEqual(len(PRODUCE_DISPLAY_NAMES), 14)
        self.assertEqual(produce_guess("Tomato__Fresh"), "Fresh Tomato")

    def test_api_auto_identifies_crop_with_expanded_checkpoint(self):
        image_path = (
            ROOT / "data" / "leaf_field_test" / "Potato___Early_blight"
            / "test_backus-056-potato-blight.jpg"
        )
        with Image.open(image_path) as source:
            image = source.convert("RGB")

        result = server.analyse_image("leaf", image)

        self.assertIn("selected_crop", result)
        self.assertIn(result["selected_crop"], {"Potato", "Tomato", "Unknown"})
        self.assertIn("crop_probability", result)
        self.assertIn("disease_supported", result)
        self.assertTrue(result["top"])
        self.assertEqual(result["task"], "leaf")
        self.assertIn("clean_accuracy", result["model_info"])


if __name__ == "__main__":
    unittest.main()
