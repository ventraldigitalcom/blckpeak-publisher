#!/usr/bin/env python3
"""One-time, user-approved Instagram-only recovery. No TikTok/YouTube writes."""
import hashlib, json, os, subprocess, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
KEY=os.getenv("BUFFER_API_KEY")
MANIFEST=ROOT/"instagram_recoveries/igrec20261103bp02.json"
RECEIPT=ROOT/"receipts/igrec20261103bp02.json"
SOURCE_APPROVAL=ROOT/"approvals/bpimage20261102a.json"
SOURCE_RECEIPT=ROOT/"receipts/bpimage20261102a.json"
EXPECTED_IMAGE="https://ventraldigitalcom.github.io/blckpeak-publisher/assets/bpimage20261102a_instagram_recovery_approved.jpg"
EXPECTED_SHA="545fc350b4aca26477d41033826c61107d794314c987da22eeb5fd8d76487cb0"
EXPECTED_IG="6ae7b1b5e29c69a1712dbcbd"

def gql(query, vars=None):
    body=json.dumps({"query":query,"variables":vars or {}}).encode()
    request=urllib.request.Request("https://api.buffer.com",data=body,method="POST",
        headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=40) as resp:
        doc=json.load(resp)
    if doc.get("errors"):
        raise RuntimeError("Buffer API errors: "+str(doc["errors"])[:300])
    return doc.get("data") or {}

def checkpoint(state):
    RECEIPT.parent.mkdir(exist_ok=True)
    RECEIPT.write_text(json.dumps(state,indent=2)+"\n")
    def run(*args): subprocess.run(args,cwd=ROOT,check=True,timeout=60)
    run("git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com")
    run("git","config","user.name","github-actions[bot]")
    run("git","add",str(RECEIPT.relative_to(ROOT)))
    run("git","commit","-m","Record one-time Instagram recovery attempt")
    run("git","push","origin","HEAD:main")

def local_date(raw):
    return datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(
         ZoneInfo("America/Chicago")).date().isoformat()

def preflight():
    if RECEIPT.exists():
        raise ValueError("One-time recovery already attempted; no duplicate requests allowed")
    if not KEY:
        raise ValueError("Buffer secret unavailable")
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    source=json.loads(SOURCE_APPROVAL.read_text(encoding="utf-8"))
    prev=json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    if (m.get("approval_id")!="igrec20261103bp02" or
        m.get("user_approved") is not True or m.get("platforms")!=["instagram"] or
        m.get("recovery_of")!="bpimage20261102a" or
        m.get("image_url")!=EXPECTED_IMAGE or
        m.get("image_sha256")!=EXPECTED_SHA or
        m.get("caption_instagram")!=source.get("caption_instagram") or
        m.get("audio_policy")!="approved_static_image_no_added_audio"):
        raise ValueError("Manifest does not match exact user-approved image, copy and Instagram-only scope")
    if prev["attempts"]["tiktok"]["status"]!="buffer_sent" or prev["attempts"]["youtube"]["status"]!="buffer_sent":
        raise ValueError("Source post delivery not verified; cannot recover safely")
    if prev["attempts"]["instagram"]["status"]!="buffer_publish_error":
        raise ValueError("Original Instagram delivery no longer failed")
    raw=m["scheduled_for"]
    if raw!="2026-11-03T19:00:00-06:00":
        raise ValueError("Only previously checked 7PM Chicago recovery slot allowed")
    due=datetime.fromisoformat(raw)
    utc_due=due.astimezone(timezone.utc)
    now=datetime.now(timezone.utc)
    if utc_due<=now+timedelta(minutes=30) or utc_due>now+timedelta(days=14):
        raise ValueError("Scheduling time is no longer safely in the future")
    with urllib.request.urlopen(urllib.request.Request(
        EXPECTED_IMAGE,headers={"User-Agent":"BLCKPEAK-exact-owner-approval"}),timeout=40) as response:
        if response.status!=200 or not response.headers.get("content-type","").lower().startswith("image/jpeg"):
            raise ValueError("Exact public media unavailable as JPEG")
        media=response.read(1000000)
    if hashlib.sha256(media).hexdigest()!=EXPECTED_SHA:
        raise ValueError("Public image is not byte-identical to user-approved file")
    organizations=(gql("query { account { organizations { id } } }").get("account") or {}).get("organizations") or []
    if len(organizations)!=1: raise ValueError("Expected one Buffer organization")
    oid=organizations[0]["id"]
    ch=gql("query($id:OrganizationId!){channels(input:{organizationId:$id}){id service isDisconnected isLocked isQueuePaused}}",{"id":oid}).get("channels") or []
    insta=[c for c in ch if c["service"]=="instagram"]
    if len(insta)!=1 or insta[0]["id"]!=EXPECTED_IG or any(insta[0][k] for k in ("isDisconnected","isLocked","isQueuePaused")):
        raise ValueError("Target Instagram account is not uniquely connected, unlocked and unpaused")
    # Fetch the full provider inventory: reject changed pending schedule or a duplicate.
    ids=[c["id"] for c in ch if c["service"] in ("instagram","tiktok","youtube")]
    posts=[];cursor=None
    query="query($input:PostsInput!,$first:Int,$after:String){posts(input:$input,first:$first,after:$after){edges{node{id channelId text status dueAt}}pageInfo{endCursor hasNextPage}}}"
    for _ in range(20):
        result=gql(query,{"input":{"organizationId":oid,"filter":{"channelIds":ids}},"first":50,"after":cursor})["posts"]
        posts.extend(x["node"] for x in result.get("edges") or [])
        if not result["pageInfo"]["hasNextPage"]:break
        cursor=result["pageInfo"]["endCursor"]
    else:raise ValueError("Post inventory truncated; cannot check duplicates")
    original_instagram_id=prev["attempts"]["instagram"]["id"]
    old=[p for p in posts if p["id"]==original_instagram_id]
    if len(old)!=1 or old[0]["status"]!="error":
        raise ValueError("Original Instagram post is no longer a confirmed media error")
    for p in posts:
        status=(p.get("status") or "").lower()
        if (p["channelId"]==EXPECTED_IG and
                (p.get("text") or "").strip()==m["caption_instagram"].strip() and
                status not in ("error","deleted")):
            raise ValueError("Duplicate Instagram caption already submitted or published: "+p["id"])
        when=p.get("dueAt")
        if (when and status not in ("error","sent","deleted") and
                local_date(when)=="2026-11-03"):
            raise ValueError("Existing pending post on checked Chicago day; slot no longer verified: "+p["id"])
    # Conservative cross-platform quota: count active/sent creative IDs from receipts;
    # cancelled-only entries do not count. The original creative counts once even on
    # TikTok and YouTube together. This recovery is the same approved creative.
    counted=set()
    for f in (ROOT/"receipts").glob("*.json"):
        row=json.loads(f.read_text())
        if row.get("scheduled_post_day")!="2026-11-03":continue
        attempts=row.get("attempts") or {}
        if any((v.get("status") or "").lower() in
               ("buffer_sent","buffer_scheduled","attempting","uncertain","buffer_queued")
               for v in attempts.values()):
            counted.add(row.get("recovery_of") or row.get("approval_id") or f.stem)
    if len(counted)>2 or (len(counted)==2 and m["recovery_of"] not in counted):
        raise ValueError("Two creative/day quota reached")
    print("PREFLIGHT_OK: exact approved image, original IG error, healthy IG business account, no duplicate, free 7PM slot, daily cap",len(counted))
    return m,utc_due

def main():
    m,due=preflight()
    state={"approval_id":m["approval_id"],"recovery_of":m["recovery_of"],
           "target":"instagram","scheduled_post_day":"2026-11-03",
           "approved_image_sha256":EXPECTED_SHA,
           "attempts":{"instagram":{"status":"attempting","note":"single-use approval checkpoint before Buffer external write"}}}
    checkpoint(state)  # If this fails, no API write occurs.
    mutation="mutation($input:CreatePostInput!){createPost(input:$input){... on PostActionSuccess{post{id status dueAt}} ... on MutationError{message}}}"
    inp={"channelId":EXPECTED_IG,"text":m["caption_instagram"],
         "assets":[{"image":{"url":EXPECTED_IMAGE,"metadata":{"altText":"BLCKPEAK handheld showerhead"}}}],
         "metadata":{"instagram":{"type":"post","shouldShareToFeed":True,"isAiGenerated":True}},
         "mode":"customScheduled",
         "dueAt":due.isoformat(timespec="milliseconds").replace("+00:00","Z"),
         "schedulingType":"automatic","needsApproval":False,"saveToDraft":False,"aiAssisted":True}
    try:
        result=(gql(mutation,{"input":inp}).get("createPost") or {})
        post=result.get("post") or {}
        if not post.get("id") or post.get("status") in ("sent","published"):
            raise RuntimeError("Buffer did not confirm a scheduled item: "+str(result)[:250])
        returned=post.get("dueAt")
        if not returned or abs((datetime.fromisoformat(returned.replace("Z","+00:00"))-due).total_seconds())>5:
            raise RuntimeError("Buffer dueAt mismatch; manually inspect post ID")
        state["attempts"]["instagram"]={"status":"buffer_scheduled","id":post["id"],"due_at":returned,"buffer_status":post.get("status")}
    except Exception as exc:
        state["attempts"]["instagram"]={"status":"uncertain","error":str(exc)[:350]}
        try:checkpoint(state)
        finally:raise
    checkpoint(state)
    print("INSTAGRAM_ONLY_SCHEDULED",json.dumps(state["attempts"]["instagram"]))
    print("No TikTok, YouTube, immediate publishing, ad spend, or new creative generation")

if __name__=="__main__":
    main()
