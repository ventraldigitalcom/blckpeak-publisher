"""Offline regression tests for the black-bar and silent-media pipeline."""
import tempfile
import unittest
import subprocess
from pathlib import Path
from scripts.media_export import portrait_crop, export_media, probe_dimensions

class FormatTests(unittest.TestCase):
    def test_original_flow_768x1376(self):
        self.assertEqual(portrait_crop(768,1376),(765,1360,1,8))
    def test_flow_native_portrait_768x1365(self):
        self.assertEqual(portrait_crop(768,1365),(765,1360,1,2))
    def test_true_1080x1920_unchanged(self):
        self.assertEqual(portrait_crop(1080,1920),(1080,1920,0,0))
    def test_incorrect_portrait_rejected(self):
        for dimensions in ((1080,1350),(1350,1080),(768,1024)):
            with self.subTest(dimensions=dimensions):
                with self.assertRaisesRegex(ValueError,"9:16"):
                    portrait_crop(*dimensions)
    def test_embedded_black_bottom_band_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            original=base/"blackband.png"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","color=c=0x3399cc:s=768x1376:d=0.1",
                "-vf","drawbox=x=0:y=1200:w=768:h=176:color=black:t=fill",
                "-frames:v","1",str(original)],check=True,timeout=30)
            from scripts.media_export import bottom_black_band_pixels
            self.assertGreater(bottom_black_band_pixels(original,768,1376),100)
            with self.assertRaisesRegex(ValueError,"black bottom band"):
                export_media(original,base/"short.mp4",base/"ig.jpg",base/"tt.jpg")

    def test_real_ffmpeg_full_bleed_and_no_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            original,mp4,ig,tiktok = (base/x for x in ("original.png","short.mp4","instagram.jpg","tiktok.jpg"))
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","color=c=0x3399cc:s=768x1376:d=0.1",
                "-frames:v","1",str(original)],check=True,timeout=30)
            result=export_media(original,mp4,ig,tiktok)
            self.assertEqual(result["crop"],(765,1360,1,8))
            self.assertEqual(probe_dimensions(mp4),(1080,1920))
            self.assertEqual(probe_dimensions(ig),(1080,1350))
            self.assertEqual(probe_dimensions(tiktok),(1080,1920))
            # Solid colored source must remain colored at bottom-left corner;
            # black pad regression would make this pixel dark.
            proc=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
                "-i",str(mp4),"-vf","crop=2:2:0:1918,format=rgb24",
                "-frames:v","1","-f","rawvideo","-"],capture_output=True,check=True,timeout=30)
            rgb=proc.stdout[:3]
            self.assertEqual(len(rgb),3)
            self.assertGreater(max(rgb),90,"Bottom corner must not be black padded")
            audio=subprocess.run(["ffprobe","-v","error","-select_streams","a",
                "-show_entries","stream=index","-of","csv=p=0",str(mp4)],
                capture_output=True,text=True,check=True,timeout=20)
            self.assertEqual(audio.stdout.strip(),"","No unlicensed audio may be embedded automatically")

if __name__=="__main__":
    unittest.main()
