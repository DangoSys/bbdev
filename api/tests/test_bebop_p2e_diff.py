import importlib.util
import runpy
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "bbdev" / "api"
sys.path.insert(0, str(API))

motia = types.ModuleType("motia")
motia.FlowContext = object
motia.queue = lambda name: name
sys.modules["motia"] = motia

event_path = API / "steps" / "bebop" / "p2e" / "03_runworkload_event.step.py"
spec = importlib.util.spec_from_file_location("bebop_p2e_runworkload_event", event_path)
event = importlib.util.module_from_spec(spec)
spec.loader.exec_module(event)


class BebopP2eDiffTest(unittest.TestCase):
    def test_bbdev_parses_diff_options(self):
        cli = runpy.run_path(str(ROOT / "bbdev" / "bbdev"))
        args = cli["parse_args"]([
            "bebop-p2e",
            "--runworkload",
            "--chip pebble --image fw_payload-lenet --bitstream image.bit "
            "--diff --golden-elf golden.elf --golden-pk",
        ])
        parsed = cli["extract_command_info"](args)["args"]
        self.assertEqual(parsed["golden-elf"], "golden.elf")
        self.assertTrue(parsed["diff"])
        self.assertTrue(parsed["golden-pk"])

    def test_diff_runtime_build_enables_bemu_and_difftest(self):
        command, cwd = event.runtime_build_command("/repo", "pebble", True, "/rtl", "/case")
        self.assertIn("--features p2e,bemu,difftest", command)
        self.assertIn("/repo/examples/chips/pebble/generated/bebop/Cargo.toml", command)
        self.assertTrue(command.endswith("--diff"))
        self.assertEqual(cwd, "/repo/examples/chips/pebble/generated/bebop")

    def test_normal_runtime_build_only_enables_p2e(self):
        cli = runpy.run_path(str(ROOT / "bbdev" / "bbdev"))
        args = cli["parse_args"]([
            "bebop-p2e",
            "--runworkload",
            "--chip pebble --image fw_payload-lenet --bitstream image.bit --diff=false",
        ])
        parsed = cli["extract_command_info"](args)["args"]
        self.assertFalse(parsed["diff"])

        command, cwd = event.runtime_build_command("/repo", "pebble", False, "/rtl", "/case")
        self.assertIn("--features p2e", command)
        self.assertNotIn("bemu", command)
        self.assertNotIn("difftest", command)
        self.assertFalse(command.endswith("--diff"))
        self.assertEqual(cwd, "/repo/bebop")


if __name__ == "__main__":
    unittest.main()
