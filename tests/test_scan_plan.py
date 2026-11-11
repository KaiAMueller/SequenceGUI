
import unittest

from gui.scan_plan import build_scan_plan


class TestScanPlan(unittest.TestCase):

    def test_linear_scan(self):
        dimensions = {
            "dim0": {
                "steps": "10",
                "variables": {
                    "BlinkTime": {
                        "mode": "linear",
                        "min": "100",
                        "max": "1000",
                    }
                },
            }
        }

        plan = build_scan_plan(dimensions)

        self.assertEqual(len(plan), 10)
        self.assertEqual(
            [point["BlinkTime"] for point in plan],
            list(range(100, 1001, 100)),
        )

    def test_multiple_dimensions(self):
        dimensions = {
            "dim0": {
                "steps": "2",
                "variables": {
                    "Frequency": {
                        "mode": "linear",
                        "min": "90",
                        "max": "100",
                    }
                },
            },
            "dim1": {
                "steps": "2",
                "variables": {
                    "Amplitude": {
                        "mode": "data list",
                        "datalist": [0.3, 0.5],
                    }
                },
            },
        }

        plan = build_scan_plan(dimensions)

        self.assertEqual(plan, [
            {"Frequency": 90.0, "Amplitude": 0.3},
            {"Frequency": 90.0, "Amplitude": 0.5},
            {"Frequency": 100.0, "Amplitude": 0.3},
            {"Frequency": 100.0, "Amplitude": 0.5},
        ])

    def test_invalid_data_list(self):
        dimensions = {
            "dim0": {
                "steps": "3",
                "variables": {
                    "BlinkTime": {
                        "mode": "data list",
                        "datalist": [100, 200],
                    }
                },
            }
        }

        with self.assertRaises(ValueError):
            build_scan_plan(dimensions)


if __name__ == "__main__":
    unittest.main()
