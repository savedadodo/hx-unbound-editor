"""Offline checks for custom display names: synthetic names only, no USB, no HX Edit."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import custom_names

PLACEMENTS = json.dumps([
    {"model": 388, "name": "Kinky Boost", "symbol": "HD2_DistKinkyBoostMono", "category": "Distortion"},
    {"model": 80, "name": "US Deluxe Nrm", "symbol": "HD2_AmpUSDeluxeNrm", "category": "Amp"},
    {"model": 380, "name": "NAM A2 Lite", "symbol": "HD2_AmpNAMLite", "category": "Amp"},
]).encode()


class CustomNames(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "names.csv"
        self.path.write_text("internal,floor_name,real_name\n"
                             "HD2_DistKinkyBoostMono,Kinky Boost,Test Boost\n"
                             "HD2_AmpNAMLite,NAM A2 Lite,Never Shown\n", encoding="utf-8")
        os.environ["HX_UNBOUND_NAMES"] = str(self.path)

    def tearDown(self):
        del os.environ["HX_UNBOUND_NAMES"]
        self.dir.cleanup()

    def test_catalog_renamed_and_stock_name_kept(self):
        rows = {r["model"]: r for r in json.loads(custom_names.catalog(PLACEMENTS))}
        self.assertEqual(("Test Boost", "Kinky Boost"), (rows[388]["name"], rows[388]["stockName"]))
        self.assertEqual("US Deluxe Nrm", rows[80]["name"])
        self.assertNotIn("stockName", rows[80])
        self.assertEqual("NAM A2 Lite", rows[380]["name"])       # NAM keeps its own naming

    def test_visual_rows(self):
        meta = json.dumps({"categories": [], "models": [{"model": 388, "name": "Kinky Boost"},
                                                        {"model": 388, "name": "Kinky Boost", "category": "Amp+Cab"}]}).encode()
        models = json.loads(custom_names.visual(meta, PLACEMENTS))["models"]
        self.assertEqual(["Test Boost", "Test Boost"], [m["name"] for m in models])

    def test_state_is_a_copy(self):
        snapshot = {"version": 3, "board": {"blocks": [{"model": 388, "name": "Kinky Boost"},
                                                       {"model": 380, "name": "My Capture"}]}}
        shown = custom_names.state(snapshot, PLACEMENTS)
        self.assertEqual(["Test Boost", "My Capture"], [b["name"] for b in shown["board"]["blocks"]])
        self.assertEqual("Kinky Boost", snapshot["board"]["blocks"][0]["name"])   # server state untouched
        self.assertNotIn("stockName", snapshot["board"]["blocks"][0])

    def test_no_file_changes_nothing(self):
        os.environ["HX_UNBOUND_NAMES"] = str(Path(self.dir.name) / "missing.csv")
        self.assertIs(PLACEMENTS, custom_names.catalog(PLACEMENTS))
        snapshot = {"board": {"blocks": [{"model": 388, "name": "Kinky Boost"}]}}
        self.assertIs(snapshot, custom_names.state(snapshot, PLACEMENTS))


if __name__ == "__main__":
    unittest.main()
