import io
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import server


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "leaf": ROOT
    / "data"
    / "leaf_field_test"
    / "Potato___Early_blight"
    / "test_backus-056-potato-blight.jpg",
    "produce": ROOT
    / "data"
    / "fruitveg"
    / "test"
    / "Apple__Healthy"
    / "FreshApple (10).jpg",
}


def _pest_sample() -> Path:
    directory = ROOT / "data" / "tomato_pests_v1" / "test" / "BA"
    return sorted(path for path in directory.iterdir() if path.is_file())[0]


class InferenceParityTests(unittest.TestCase):
    def test_api_adapter_matches_streamlit_model_pipeline(self):
        samples = {**SAMPLES, "pest": _pest_sample()}

        for task, path in samples.items():
            with self.subTest(task=task, image=path.name):
                with Image.open(path) as source:
                    image = server.original_app.read_image(io.BytesIO(path.read_bytes()))
                original_task = "tomato_pest" if task == "pest" else task
                original = server.original_app.analyse(original_task, image)
                with patch.object(server.original_app, "analyse", return_value=original):
                    adapted = server.analyse_image(task, image)

                expected_labels = [
                    original["classes"][index] for index in original["order"][:3]
                ]
                self.assertEqual(
                    [guess["label"] for guess in adapted["top"]],
                    expected_labels,
                )
                for guess, index in zip(adapted["top"], original["order"][:3]):
                    self.assertAlmostEqual(
                        guess["prob"], float(original["probs"][index]), places=7
                    )
                self.assertEqual(adapted["images"]["photo"], server._data_url(original["view"]))
                self.assertEqual(adapted["images"]["heatmap"], server._data_url(original["overlay"]))
                self.assertEqual(adapted["task"], task)
                if task == "leaf":
                    self.assertEqual(adapted["selected_crop"], original["crop"])
                    self.assertEqual(adapted["crop_probability"], original["crop_probability"])
                    self.assertEqual(adapted["crop_supported"], original["crop_supported"])
                    self.assertEqual(
                        adapted["disease_supported"], original["disease_supported"]
                    )
                    expected_confidence = (
                        original["crop_supported"]
                        and original["crop_probability"] >= server.CONF_OK
                        and (
                            not original["disease_supported"]
                            or adapted["top"][0]["prob"] >= server.CONF_OK
                        )
                    )
                    self.assertEqual(adapted["confident"], expected_confidence)
                elif task == "produce":
                    self.assertEqual(adapted["fruit"]["name"], original["produce"])
                    self.assertEqual(adapted["fruit"]["prob"], original["produce_probability"])
                    self.assertEqual(adapted["state"]["name"], original["grade"])
                    self.assertEqual(adapted["state"]["prob"], original["grade_probability"])
                    self.assertEqual(
                        adapted["confident"],
                        original["produce_probability"] >= server.CONF_OK
                        and original["grade_probability"] >= server.CONF_OK,
                    )
                else:
                    self.assertEqual(adapted["confident"], original["confident"])
                    self.assertEqual(adapted["not_target"], original["not_target"])


if __name__ == "__main__":
    unittest.main()
