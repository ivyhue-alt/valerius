import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_scenarios  # noqa: E402


class RepeatClaims(unittest.TestCase):
    def test_all_scenarios_behave_as_expected(self):
        with contextlib.redirect_stdout(io.StringIO()):
            passed, total = run_scenarios.run(verbose=False)
        self.assertEqual(passed, total)
        self.assertGreaterEqual(total, 25)


if __name__ == "__main__":
    unittest.main()
