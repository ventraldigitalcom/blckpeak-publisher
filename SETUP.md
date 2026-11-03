# BLCKPEAK cloud publisher — PAUSED after 2026-11-03 media issue

**Status:** New automatic scheduling is disabled in `.github/workflows/publish.yml` (`if: ${{ false }}`). Do not re-enable on the strength of automated tests alone.

## Incident and confirmed actions (November 3, 2026)
- User observed a TikTok photo post with an apparent black area beneath the picture, and no music.
- GitHub's earlier YouTube video converter used `scale=...:decrease,pad=...`, which can create black letterboxing. The TikTok photo post used the original Shopify source URL directly rather than a validated 1080×1920 export. The screenshot by itself cannot establish whether TikTok's black area is an embedded border or the app viewer.
- Disabled the publish stage for all *new* manifest executions.
- Cancelled exactly three Buffer posts scheduled for November 3 at 7 PM America/Chicago (one each Instagram, TikTok and YouTube); confirmation in GitHub Actions run 41713725728. This did not undo any already-published post.
- Replaced the export with a centered exact 9:16 integer crop (up to 2.5% of source edges), Lanczos 1080×1920 render and **no black padding**. Sources significantly off 9:16 are rejected for manual review, not drastically cropped.
- New TikTok media uses the finished 1080×1920 image; YouTube uses a true-frame eight-second MP4. Instagram uses a 4:5 image, preserving the full source within a blurred-source side fill. Output sizes are verified with ffprobe. Regression tests generate actual media and check a bottom corner for black letterboxing.
- Cloud source audit run [41715568282](https://github.com/ventraldigitalcom/blckpeak-publisher/actions/runs/41715568282) downloaded both actual Shopify originals: each **768×1376**, each **0 contiguous near-black bottom rows**, and each successfully exported to 1080×1920 TikTok/Shorts and 1080×1350 Instagram. Thus the original files do not contain a full-width black bottom border; the screenshot may reflect TikTok viewer framing or caption area. Platform-render validation is still necessary.
- Important: an actual private/controlled platform test and full BLCKPEAK product visual inspection are still mandatory before reactivation.

## Verified three-platform delivery diagnosis (read-only Buffer, 2026-11-03)

- For the approved 1 PM Chicago post `bpimage20261102a`, TikTok reports `sent` with [published TikTok link](https://tiktok.com/@blackpeakventures/video/7704022396906294541).
- YouTube likewise reports `sent` to connected **BlackPeak Ventures** channel, with [this Shorts link](https://www.youtube.com/shorts/n531NNG-n30). Buffer reports successful handoff but we could not independently load the YouTube page in the diagnostic environment; user can check the linked channel.
- Instagram returned `error`: **There is an issue with the media included. Please remove it and try to upload it again.** Its previous directly supplied original was 768x1376 (ratio .558), below Instagram automatic feed minimum of 4:5 (.8); this explains the likely media rejection. Instagram account `blackpeakventures` is a connected business profile, not locked or disconnected.
- New production media conversion is now exercised with the *actual approved source* through `python3 scripts/publisher.py prepare` in the cloud without contacting Buffer. Verified 1080x1920 H.264 Short, 1080x1920 TikTok JPG and 1080x1350 Instagram JPG. [Dry-run proof](https://github.com/ventraldigitalcom/blckpeak-publisher/actions/runs/41718995767).
- Publisher now optionally supports an explicitly approved `"platforms": ["instagram"]` manifest, so recovering one failed Instagram image will NOT duplicate the already published TikTok/YouTube posts.
- Existing receipt `receipts/bpimage20261102a.json` now records actual individual delivery states, not merely scheduled acceptance. No automatic retry or re-publication of the corrected Instagram design has been authorized.
- All new publishing remains disabled by the explicit workflow hold. The corrected Instagram asset and caption need human approval and a separately scheduled controlled test before changing that.

## Music limitations
- Buffer **cannot add TikTok's native/trending music automatically** through its publishing API; TikTok notification-publishing plus manual finalization in the app is required for native sounds.
- Instagram post/story music also requires native app finishing via notification publishing; some eligible connected Instagram Reel flows support music separately. Never assume an audio selection transfers cross-platform.
- This publisher does not include any unlicensed music. A new `audio_policy: "silent_explicitly_approved"` manifest field is required before any automatic silent post; old approvals without this explicit audio choice will **not** silently publish even if the workflow is later re-enabled.
- A future approved, independently licensed original audio track could be embedded into approved videos only if rights and platform-specific use have been verified, plus the owner approves the exact creative+audio. No such integration is currently deployed.
- Do not represent silence as music, or claimed trending sounds as automatically embedded.

## Owner approval contract and safety
1. Creative-generation schedule remains 7 AM, 1 PM and 7 PM America/Chicago (three distinct 9:16 image candidates per batch), separate from social posting.
2. Preserve canonical BLACK/GREY/SILVER SKU geometry and reject inaccurate/floating cutouts before showing A/B/C. User can select multiple or NONE; NONE never posts.
3. Only exact explicitly approved image **and displayed copy** may be scheduled. A/B/C selection does not allow unapproved audio, new AI versions, or immediate posting.
4. Max two distinct approved creatives per Chicago calendar day across all platforms; no automatic queue rollover is guaranteed.
5. All paid advertising or spend prohibited. Buffer secret only in GitHub Actions secrets; never paste it into repo or chat.
6. Publishing must use `customScheduled`/`dueAt`, not `shareNow`. No uncontrolled test posts.
7. Before unpausing, audit Buffer Calendar for leftovers, source image and final media visually, validate the exact audio policy, secure user approval for a controlled test, and confirm final results independently in TikTok, Instagram and YouTube.

## Cloud environment
- Flow image generation / ChatGPT Work cloud browser requires authenticated cloud access and is not guaranteed unattended by these GitHub Actions media checks. No local computer must be relied upon for GitHub conversion.
- This repo's GitHub Pages URL hosts approved media. The read-only Buffer connection and previous scheduled posts show API connectivity, but do not constitute a new successful post-QC live test.

## Verification links
- Emergency Buffer cancellations: https://github.com/ventraldigitalcom/blckpeak-publisher/actions/runs/41713725728
- Latest safety runs: https://github.com/ventraldigitalcom/blckpeak-publisher/actions
