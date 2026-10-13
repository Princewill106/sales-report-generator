import unittest

import main


class ReportTests(unittest.TestCase):
    def test_week_split(self):
        r = main.build(main.load("sample_sales.csv"))
        self.assertEqual(str(r["start"]), "2026-09-29")
        self.assertEqual(r["k1"]["orders"], 9)
        self.assertEqual(r["movers"][0][0], "Smoothie")
        self.assertEqual(r["branches"][0][0], "Lekki")


if __name__ == "__main__":
    unittest.main()
