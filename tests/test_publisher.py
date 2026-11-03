"""Offline unit checks: no Buffer credentials, media hosting, or social posts."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "publisher.py"
spec = importlib.util.spec_from_file_location("blckpeak_publisher", SOURCE)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

class ApprovalChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.old_root = publisher.ROOT
        self.old_receipts = publisher.RECEIPTS
        self.old_env = os.environ.get("APPROVAL_FILE")
        publisher.ROOT = Path(self.folder.name)
        publisher.RECEIPTS = publisher.ROOT / "receipts"
        (publisher.ROOT / "approvals").mkdir()
        os.environ["APPROVAL_FILE"] = "approvals/20261101A001.json"
        self.sample = dict(
            approval_id="20261101A001",chosen="A",user_approved=True,
            image_url="https://cdn.shopify.com/s/files/approved-image.png",
            caption_instagram="BLCKPEAK showerhead #shower",
            caption_tiktok="BLCKPEAK showerhead #shower",
            caption_youtube="BLCKPEAK showerhead #shorts",
            youtube_title="BLCKPEAK Showerhead | #Shorts",
            scheduled_for=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
        )
    def tearDown(self):
        publisher.ROOT = self.old_root
        publisher.RECEIPTS = self.old_receipts
        if self.old_env is None: os.environ.pop("APPROVAL_FILE", None)
        else: os.environ["APPROVAL_FILE"] = self.old_env
    def put(self):
        (publisher.ROOT / os.environ["APPROVAL_FILE"]).write_text(json.dumps(self.sample))
    def test_approved_A(self):
        self.put()
        self.assertEqual(publisher.approval()["chosen"],"A")
    def test_instagram_only_recovery_target(self):
        self.sample["platforms"]=["instagram"]
        self.put()
        approved=publisher.approval()
        self.assertEqual(approved["platforms"],["instagram"])

    def test_duplicate_or_unapproved_platform_targets_rejected(self):
        for targets in ([],["instagram","instagram"],["youtube","facebook"],"instagram"):
            with self.subTest(platforms=targets):
                self.sample["platforms"]=targets
                self.put()
                with self.assertRaisesRegex(ValueError,"platform"):
                    publisher.approval()

    def test_schedule_required(self):
        del self.sample["scheduled_for"]; self.put()
        with self.assertRaisesRegex(ValueError,"scheduled_for"): publisher.approval()
    def test_timezone_required(self):
        self.sample["scheduled_for"]="2026-11-04T19:00:00"; self.put()
        with self.assertRaisesRegex(ValueError,"timezone"): publisher.approval()
    def test_past_schedule_never_posts_immediately(self):
        self.sample["scheduled_for"]="2020-01-01T19:00:00-06:00"; self.put()
        with self.assertRaisesRegex(ValueError,"past"): publisher.due_at_utc(publisher.approval())
    def test_utc_conversion(self):
        self.sample["scheduled_for"]="2026-12-01T19:00:00-06:00"
        self.assertEqual(publisher.scheduled_at(self.sample).isoformat(),"2026-12-02T01:00:00+00:00")
    def test_future_scheduling_only(self):
        import inspect
        code=inspect.getsource(publisher.publish)
        self.assertIn('"customScheduled"',code)
        self.assertNotIn('"shareNow"',code)
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
    def test_daily_limit_allows_two_creatives(self):
        day=publisher.scheduled_at(self.sample).astimezone(ZoneInfo("America/Chicago")).date().isoformat()
        publisher.RECEIPTS.mkdir()
        row={"approval_id":"FIRST","scheduled_post_day":day,"attempts":{"instagram":{"status":"attempting"}}}
        (publisher.RECEIPTS/"first.json").write_text(json.dumps(row))
        current=publisher.enforce_daily_post_cap(self.sample,{"approval_id":self.sample["approval_id"],"attempts":{}})
        self.assertEqual(current["scheduled_post_day"],day)
    def test_daily_limit_blocks_third_creative(self):
        day=publisher.scheduled_at(self.sample).astimezone(ZoneInfo("America/Chicago")).date().isoformat()
        publisher.RECEIPTS.mkdir()
        for idx in range(2):
            row={"approval_id":"OLDER"+str(idx),"scheduled_post_day":day,"attempts":{"youtube":{"status":"buffer_scheduled"}}}
            (publisher.RECEIPTS/("older"+str(idx)+".json")).write_text(json.dumps(row))
        with self.assertRaisesRegex(RuntimeError,"Two-post daily cap"):
            publisher.enforce_daily_post_cap(self.sample,{"approval_id":self.sample["approval_id"],"attempts":{}})
    def test_silent_post_requires_explicit_audio_approval(self):
        self.put()
        previous=os.environ.get("PUBLISHING_ENABLED")
        os.environ["PUBLISHING_ENABLED"]="true"
        try:
            with self.assertRaisesRegex(ValueError,"Silent automatic post"):
                publisher.publish(publisher.approval())
        finally:
            if previous is None: os.environ.pop("PUBLISHING_ENABLED",None)
            else: os.environ["PUBLISHING_ENABLED"]=previous

    def test_github_actions_direct_cli_imports_work(self):
        # The Actions workflow runs "python3 scripts/publisher.py prepare", not -m.
        import subprocess, sys
        proc=subprocess.run([sys.executable,str(SOURCE),"prepare"],
             cwd=SOURCE.parents[1],capture_output=True,text=True,timeout=20,
             env={**os.environ,"APPROVAL_FILE":""})
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("Missing canonical explicit approval filename",proc.stderr)
        self.assertNotIn("ModuleNotFoundError",proc.stderr)

    def test_no_publishing_flag(self):
        flag=os.environ.pop("PUBLISHING_ENABLED",None)
        self.put()
        try:
            with self.assertRaises(ValueError):publisher.publish(publisher.approval())
        finally:
            if flag is not None:os.environ["PUBLISHING_ENABLED"]=flag

if __name__=="__main__":
    unittest.main()
