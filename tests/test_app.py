import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


class AppIntegrationTests(unittest.TestCase):
    def test_empty_app_and_standalone_simulator(self):
        app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        app.radio(key="workspace").set_value("概率模拟").run()
        self.assertFalse(app.exception)
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["平均UP数量 · 精确"], "20.57")
        self.assertEqual(metrics["平均出金数 · 精确"], "31.02")

    def test_history_comparison_forecast_and_clear(self):
        app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30)
        app.session_state["raw_data"] = pd.DataFrame({"时间": ["", "", ""], "角色名": ["角色A", "角色B", "角色C"], "是UP?": ["是", "是", "否"], "抽数": [30, 70, 60]})
        app.session_state["tail_pity"] = 25
        app.run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == "用我的总抽数对比模拟").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="sim_pulls").value, 185)
        self.assertEqual(app.number_input(key="sim_pity").value, 0)
        self.assertTrue(any(m.label == "我的UP数" and m.value == "2" for m in app.metric))
        app.radio(key="workspace").set_value("抽卡记录").run()
        next(b for b in app.button if b.label == "从当前保底状态继续模拟").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.number_input(key="sim_pity").value, 25)
        self.assertTrue(app.checkbox(key="sim_guaranteed").value)
        self.assertEqual(len(app.session_state["raw_data"]), 3)
        next(b for b in app.button if b.label == "清空当前终端").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["raw_data"].empty)
        self.assertEqual(app.session_state["tail_pity"], 0)


if __name__ == "__main__":
    unittest.main()
