import tempfile
import unittest
from pathlib import Path

import pandas as pd

from forest_fire_detection.preprocessing.labels import TYPING_LABELS_V1, read_labels_v1


class LabelTimezoneTests(unittest.TestCase):
    def test_local_times_are_converted_to_utc(self):
        base = {column: 1 if dtype in (int, float) else "value" for column, dtype in TYPING_LABELS_V1.items()}
        cases = [
            ("MADRID", "2023-01-15 12:00:00", "15/01/2023 13:00:00", "2023-01-15 11:00:00+00:00"),
            ("CANARIAS", "2023-01-15 12:00:00", "15/01/2023 13:00:00", "2023-01-15 12:00:00+00:00"),
            ("MADRID", "2023-07-15 12:00:00", "15/07/2023 13:00:00", "2023-07-15 10:00:00+00:00"),
            ("CANARIAS", "2023-07-15 12:00:00", "15/07/2023 13:00:00", "2023-07-15 11:00:00+00:00"),
            ("MADRID", "2023-03-26 02:30:00", "29/10/2023 02:30:00", None),
        ]
        rows = [dict(base, Comunidad=community, Detectado=detected, Extinguido=extinguished, NumeroParte=str(i))
                for i, (community, detected, extinguished, _) in enumerate(cases)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.csv"
            pd.DataFrame(rows).to_csv(path, index=False)
            raw, processed = read_labels_v1(str(path))

        processed = processed.set_index("NumeroParte")
        for i, (_, _, _, expected) in enumerate(cases):
            detected = processed.loc[str(i), "Detectado"]
            if expected is None:
                self.assertTrue(pd.isna(detected))
                self.assertTrue(pd.isna(processed.loc[str(i), "Extinguido"]))
            else:
                self.assertEqual(detected, pd.Timestamp(expected))
                self.assertEqual(processed.loc[str(i), "Extinguido"], detected + pd.Timedelta(hours=1))
        self.assertEqual(str(processed["Detectado"].dtype.tz), "UTC")
        self.assertEqual(str(processed["Extinguido"].dtype.tz), "UTC")
        self.assertEqual(raw.loc[0, "Detectado"], cases[0][1])


if __name__ == "__main__":
    unittest.main()
