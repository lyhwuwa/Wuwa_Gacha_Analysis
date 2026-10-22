import unittest

import numpy as np
import pandas as pd

from gacha_model import CDF, MEAN_GOLD, MEAN_UP, exact_expectations, gold_probability, percentile_interval, sample_account, simulate
from record_analysis import analyze_records, empty_records, export_backup, merge_records, read_backup


class ModelTests(unittest.TestCase):
    def test_curve_boundaries(self):
        for n, expected in [(1, .008), (65, .008), (66, .048), (70, .208), (71, .288), (75, .608), (76, .708), (78, .908), (79, 1)]:
            self.assertAlmostEqual(gold_probability(n), expected)
        self.assertAlmostEqual(MEAN_GOLD, 54.10274378649243)
        self.assertAlmostEqual(MEAN_UP, 81.15411567973865)

    def test_one_draw_with_and_without_guarantee(self):
        self.assertAlmostEqual(exact_expectations(1)["up"], .004)
        self.assertAlmostEqual(exact_expectations(1, 78)["up"], .5)
        forced = exact_expectations(1, 78, True)
        self.assertEqual(forced["up"], 1)
        self.assertEqual(forced["gold"], 1)
        self.assertEqual(forced["end_pity"], 0)
        self.assertEqual(forced["end_guarantee"], 0)
        self.assertEqual(exact_expectations(0, 23, True)["end_pity"], 23)

    def test_1700_cross_check_independent_renewal_equation(self):
        theory = exact_expectations(1700)
        pmf = np.diff(np.r_[0, CDF])
        renewal = np.zeros(1701)
        for n in range(1, 1701):
            k = min(n, 79)
            renewal[n] = np.dot(pmf[:k], 1 + renewal[n-k:n][::-1])
        self.assertAlmostEqual(theory["gold"], renewal[1700], places=9)
        self.assertAlmostEqual(theory["up"], 20.570681093335864, places=9)
        self.assertAlmostEqual(theory["probability_mass"], 1, places=10)

    def test_simulation_agrees_with_theory(self):
        result = simulate(1700, trials=30000, seed=20261022)
        theory = exact_expectations(1700)
        for field in ["up", "gold"]:
            self.assertLess(abs(result[f"{field}_mean"] - theory[field]), 6 * result[f"{field}_se"])
        self.assertTrue((result["up_counts"] <= result["gold_counts"]).all())
        self.assertGreaterEqual(result["up_counts"].min(), 10)

    def test_simulation_pity_and_end_state(self):
        result = simulate(1, trials=1000, pity=78, guaranteed=True)
        np.testing.assert_array_equal(result["up_counts"], np.ones(1000))
        for seed in range(10):
            sample = sample_account(300, seed=seed)
            self.assertLess(sample["end_pity"], 79)
            self.assertEqual(sample["events"][-1]["本次第几抽"] + sample["end_pity"], 300)
            for a, b in zip(sample["events"], sample["events"][1:]):
                if a["结果"] == "歪":
                    self.assertEqual(b["结果"], "大保底UP")
            self.assertTrue(all(1 <= e["出金间隔"] <= 79 for e in sample["events"]))

    def test_seed_reproduction_and_ties(self):
        a, b = simulate(100, 1000, seed=42), simulate(100, 1000, seed=42)
        np.testing.assert_array_equal(a["up_counts"], b["up_counts"])
        self.assertEqual(percentile_interval([1, 2, 2, 3], 2), (.25, .75))


class RecordTests(unittest.TestCase):
    def records(self, outcomes, costs):
        return pd.DataFrame({"角色名": [f"角色{i}" for i in range(len(costs))], "是UP?": outcomes, "抽数": costs})

    def test_completed_cycles_and_unfinished_investment(self):
        _, stats = analyze_records(self.records(["否", "是", "是", "否"], [70, 60, 30, 65]), tail_pity=20)
        self.assertEqual(stats["UP数"], 2)
        self.assertEqual(stats["UP平均花费"], 80)
        self.assertEqual(stats["总投入"], 245)
        self.assertEqual(stats["预算每UP"], 122.5)
        self.assertEqual(stats["未完成UP投入"], 85)
        self.assertTrue(stats["下次大保底"])
        self.assertAlmostEqual(stats["不歪率"], 1 / 3)

    def test_missing_up_is_not_zero_cost(self):
        _, stats = analyze_records(self.records(["否"], [70]), 12)
        self.assertIsNone(stats["UP平均花费"])
        self.assertEqual(stats["未完成UP投入"], 82)
        self.assertEqual(stats["总出金"], 1)

    def test_inherited_pulls_and_initial_guarantee(self):
        _, stats = analyze_records(self.records(["是"], [70]))
        self.assertEqual(stats["UP平均花费"], 70)
        _, stats = analyze_records(self.records(["是"], [30]), initial_guaranteed=True)
        self.assertIsNone(stats["不歪率"])
        self.assertEqual(stats["小保底次数"], 0)

    def test_invalid_sequences_and_legacy_80_preserved(self):
        output, stats = analyze_records(self.records(["否", "否"], [80, 40]))
        self.assertEqual(output.iloc[0]["抽数"], 80)
        self.assertFalse(stats["可对比"])
        self.assertEqual(len(stats["问题"]), 2)
        _, stats = analyze_records(self.records(["是", "是"], ["bad", 10.5]))
        self.assertEqual(stats["总出金"], 0)
        self.assertEqual(len(stats["问题"]), 2)

    def test_import_repeat_preserves_real_identical_rows(self):
        record = pd.DataFrame({"角色名": ["同一角色", "同一角色"], "是否UP?": ["是", "是"], "抽数": [70, 70]})
        first = merge_records(empty_records(), record)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(merge_records(first, record)), 2)
        self.assertEqual(list(first.columns), ["时间", "角色名", "是UP?", "抽数"])

    def test_backup_roundtrip_includes_pity(self):
        frame = self.records(["否", "是"], [70, 65])
        data = export_backup(frame, 36, True)
        restored, settings = read_backup(data, "backup.xlsx")
        self.assertEqual(restored["抽数"].tolist(), [70, 65])
        self.assertEqual(settings, {"tail_pity": 36, "initial_guaranteed": True})


if __name__ == "__main__":
    unittest.main()
