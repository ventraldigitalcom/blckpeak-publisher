"""Offline safety checks; never contact Buffer."""
import importlib.util, tempfile, unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/"scripts"/"instagram_recovery_once.py"
spec=importlib.util.spec_from_file_location("instagram_recovery_once",SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class RecoverySafety(unittest.TestCase):
    def test_local_timezone(self):
        self.assertEqual(module.local_date("2026-11-04T01:00:00.000Z"),"2026-11-03")
    def test_receipt_blocks_duplicate_before_any_network(self):
        with tempfile.TemporaryDirectory() as folder:
            old=module.RECEIPT
            try:
                module.RECEIPT=Path(folder)/"receipt.json"
                module.RECEIPT.write_text("{}")
                with self.assertRaisesRegex(ValueError,"already attempted"):
                    module.preflight()
            finally:
                module.RECEIPT=old
if __name__=="__main__":unittest.main()
