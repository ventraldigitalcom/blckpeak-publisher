# BLCKPEAK Cloud Publisher — status: NOT LIVE

This public repo contains source code for an approval-gated publishing prototype. **Nothing can publish while the GitHub Actions repository variable `PUBLISHING_ENABLED` is absent or not `true`.** The Buffer API key must be stored only as a GitHub Actions secret, never committed or pasted into chat.

## Owner steps still required
1. GitHub → this repo → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. Buffer → Settings → API → Personal Access → New Key. Copy it straight into GitHub → this repo → Settings → Secrets and variables → Actions → **New repository secret** named `BUFFER_API_KEY`.
3. Make sure Buffer has exactly one Instagram, one TikTok, and one YouTube channel connected. Verify automatic publishing is supported on each.
4. Run a **dry test using a separately approved test asset**. DO NOT enable publishing until we verify Pages hosting, Buffer schema, and each platform's posting options. A Buffer API acceptance is not confirmation the post appeared on the social platform.
5. Only after explicit owner-approved live test, set GitHub Actions repository variable `PUBLISHING_ENABLED=true` to enable publishing on future approvals.

## Approval contract
The original ChatGPT schedule is 7:00 AM, 1:00 PM, and 7:00 PM America/Chicago. Three distinct photorealistic 9:16 BLCKPEAK showerhead ads are attempted per batch. No generated ads that fail SKU fidelity or natural integration must be published. The user chooses A, B, C, or NONE; **NONE creates no approval manifest and publishes nothing**.

For A/B/C only, the approved image may be uploaded via the connected Shopify image-host tool then a new `approvals/<id>.json` committed to this repo by ChatGPT's connected GitHub tool. Only use exact verified approved image URLs from `cdn.shopify.com`, `blckpeak.com`, or `www.blckpeak.com`. The approval JSON must contain `approval_id`, `chosen`, `user_approved: true`, `image_url`, `caption_instagram`, `caption_tiktok`, `caption_youtube`, and `youtube_title`. Include no secrets or private customer data. Public approved creative is meant to be publicly accessible.

GitHub Actions will make an 8-second silent 1080×1920 H.264 MP4 for YouTube, create a no-crop Instagram-compatible JPG, deploy those to public GitHub Pages, and request immediate **organic** posting via Buffer API if and only if the user has selected A/B/C and publishing is enabled. No paid ads, no spending. Never treat one logged-in browser or API acceptance as proof social publishing succeeded. Server/account limits and social reauthorizations may require attention. The automation itself does not guarantee unlimited or perfectly faithful AI-generated ads.
