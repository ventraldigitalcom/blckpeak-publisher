"""Offline unit checks: no Buffer credentials, media hosting, or social posts."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "publisher.py"
spec = importlib.util.spec_from_file_location("blckpeak_publisher", SOURCE)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

class ApprovalChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.old_root = publisher.ROOT
        self.old_env = os.environ.get("APPROVAL_FILE")
        publisher.ROOT = Path(self.folder.name)
        (publisher.ROOT / "approvals").mkdir()
        os.environ["APPROVAL_FILE"] = "approvals/20261101A001.json"
        self.sample = dict(
            approval_id="20261101A001",chosen="A",user_approved=True,
            image_url="https://cdn.shopify.com/s/files/approved-image.png",
            caption_instagram="BLCKPEAK showerhead #shower",
            caption_tiktok="BLCKPEAK showerhead #shower",
            caption_youtube="BLCKPEAK showerhead #shorts",
            youtube_title="BLCKPEAK Showerhead | #Shorts"
        )
    def tearDown(self):
        publisher.ROOT = self.old_root
        if self.old_env is None: os.environ.pop("APPROVAL_FILE", None)
        else: os.environ["APPROVAL_FILE"] = self.old_env
    def put(self):
        (publisher.ROOT / os.environ["APPROVAL_FILE"]).write_text(json.dumps(self.sample))
    def test_approved_A(self):
        self.put()
        self.assertEqual(publisher.approval()["chosen"],"A")
    def test_no_approval(self):
        self.sample["user_approved"]=False; self.put()
        with self.assertRaises(ValueError):publisher.approval()
    def test_none_must_not_post(self):
        self.sample["chosen"]="NONE"; self.put()
        with self.assertRaises(ValueError):publisher.approval()
    def test_wrong_host_is_rejected(self):
        self.sample["image_url"]="https://attacker.example.com/image.png"; self.put()
        with self.assertRaises(ValueError):publisher.approval()
    def test_wrong_name_is_rejected(self):
        self.sample["approval_id"]="not-matching"; self.put()
        with self.assertRaises(ValueError):publisher.approval()
    def test_no_publishing_flag(self):
        flag=os.environ.pop("PUBLISHING_ENABLED",None)
        self.put()
        try:
            with self.assertRaises(ValueError):publisher.publish(publisher.approval())
        finally:
            if flag is not None:os.environ["PUBLISHING_ENABLED"]=flag

if __name__=="__main__":
    unittest.main()
