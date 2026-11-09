"""Offline numeric regressions: only the pure risk checker, never broker code."""
import datetime
import unittest
from unittest.mock import patch

from _load import load

risk = load("trader-risk", "check")


class FiniteNumbers(unittest.TestCase):
    def evaluate(self, **fields):
        order = {"symbol": "AAPL", "side": "buy", "qty": "1",
                 "type": "market", "time_in_force": "day"}
        order.update(fields)
        # All inputs are in memory. Any accidental file or network access fails.
        with patch("builtins.open", side_effect=AssertionError("file access")), \
                patch("socket.socket", side_effect=AssertionError("network access")), \
                patch("subprocess.Popen", side_effect=AssertionError("process access")):
            return risk.check([order], {"budget": 5000, "require_stop": False,
                                       "min_reward_risk": 0},
                              prices={"AAPL": 100},
                              now=datetime.datetime(2026, 10, 19, 14, 15))

    def test_valid_control_passes(self):
        self.assertEqual(self.evaluate()["pass"], 1)

    def test_nonfinite_order_fields_block_without_crashing(self):
        for field in risk.PRICE_FIELDS:
            for value in ("NaN", "Infinity", "-Infinity", "1e309"):
                with self.subTest(field=field, value=value):
                    fields = {field: value}
                    if field == "notional":
                        fields["qty"] = None
                    result = self.evaluate(**fields)
                    self.assertEqual(result["block"], 1)
                    self.assertTrue(any("format: " + field in reason
                                        for reason in result["results"][0]["reasons"]))
                    self.assertEqual(result["cash_after"], 5000)

    def test_numeric_helper_rejects_nonfinite_and_overflow(self):
        for value in (float("nan"), float("inf"), float("-inf"), 10 ** 1000):
            with self.subTest(value=repr(value)):
                self.assertIsNone(risk._f(value))
        self.assertEqual(risk._f("12.50"), 12.5)

    def test_invalid_quotes_are_not_loaded(self):
        prices, times = risk.load_prices({"prices": {"AAPL": "NaN", "MSFT": "Infinity"}})
        self.assertEqual((prices, times), ({}, {}))


if __name__ == "__main__":
    unittest.main()
