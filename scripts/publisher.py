#!/usr/bin/env python3
"""BLCKPEAK approved-only organic publisher. No uploads on NONE or without GitHub opt-in."""
import json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
# Works both as python3 scripts/publisher.py (GitHub Action) and via unittest.
try:
    from scripts.media_export import export_media, probe_dimensions
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from media_export import export_media, probe_dimensions

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RECEIPTS = ROOT / "receipts"
BUFFER_ENDPOINT = "https://api.buffer.com"

def execute(*args):
    subprocess.run(args, cwd=ROOT, check=True, timeout=300)

def scheduled_at(obj):
    """Read an exact, timezone-aware scheduled date. Never infer a time."""
    raw=obj.get("scheduled_for")
    if not isinstance(raw,str) or not raw.strip():
        raise ValueError("Missing exact scheduled_for date and time")
    try:
        date=datetime.fromisoformat(raw.strip().replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("scheduled_for must be ISO 8601") from exc
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("scheduled_for must have a timezone offset")
    return date.astimezone(timezone.utc)

def due_at_utc(obj):
    """Buffer requires UTC. Never permit past dates or immediate publishing."""
    date=scheduled_at(obj)
    now=datetime.now(timezone.utc)
    if date <= now + timedelta(minutes=15):
        raise ValueError("Scheduled time is past or less than 15 minutes away; no immediate posting")
    if date > now + timedelta(days=60):
        raise ValueError("Scheduled time is too far ahead; use within 60 days")
    return date.isoformat(timespec="milliseconds").replace("+00:00","Z")

def approval():
    filename = os.getenv("APPROVAL_FILE", "")
    if not re.fullmatch(r"approvals/[A-Za-z0-9_-]{8,72}\.json", filename):
        raise ValueError("Missing canonical explicit approval filename")
    path = ROOT / filename
    if not path.is_file() or path.is_symlink():
        raise ValueError("Approval manifest missing")
    obj = json.loads(path.read_text(encoding="utf-8"))
    needed = ("approval_id","chosen","user_approved","image_url",
              "caption_instagram","caption_tiktok","caption_youtube","youtube_title")
    if not all(k in obj for k in needed):
        raise ValueError("Incomplete approval manifest")
    if obj["approval_id"] != path.stem or obj["user_approved"] is not True or obj["chosen"] not in ("A","B","C"):
        raise ValueError("User has NOT explicitly approved A/B/C; NONE must not post")
    if not all(isinstance(obj[k],str) and obj[k].strip() for k in needed if k not in ("user_approved",)):
        raise ValueError("Missing approval metadata")
    url = urllib.parse.urlparse(obj["image_url"])
    if url.scheme != "https" or url.username or url.password or (url.hostname or "").lower() not in ("cdn.shopify.com","blckpeak.com","www.blckpeak.com"):
        raise ValueError("Refuse untrusted image host")
    scheduled_at(obj)
    return obj

def paths(obj):
    folder = DOCS / "assets"
    folder.mkdir(parents=True, exist_ok=True)
    ident = obj["approval_id"]
    return (folder / (ident + ".mp4"), folder / (ident + "_instagram.jpg"),
            folder / (ident + "_tiktok.jpg"))

def prepare(obj):
    mp4, jpg, tiktok = paths(obj)
    request=urllib.request.Request(obj["image_url"],headers={"User-Agent":"BLCKPEAK-publisher"})
    with urllib.request.urlopen(request,timeout=40) as response:
        if not response.headers.get("content-type","").lower().startswith("image/"):
            raise ValueError("Approval URL does not return an image")
        content=response.read(15000001)
    if len(content)>15000000 or not content:
        raise ValueError("Approved photo too large/empty")
    target=Path("/tmp/blckpeak_approved_photo")
    target.write_bytes(content)
    # Always re-create: earlier releases used black-padded media.
    report=export_media(target,mp4,jpg,tiktok)
    print("Validated source-preserving portrait media:",report)
    print("WARNING: format QC does not establish physical SKU fidelity")

def urls(obj):
    base=os.getenv("PAGES_BASE_URL","").rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("Missing GitHub Pages HTTPS deployment URL")
    prefix=base+"/assets/"+obj["approval_id"]
    return prefix+".mp4",prefix+"_instagram.jpg",prefix+"_tiktok.jpg"

def verify(obj):
    mp4,jpg,tiktok=paths(obj)
    for file,expected in ((mp4,(1080,1920)),(jpg,(1080,1350)),(tiktok,(1080,1920))):
        if not file.is_file() or probe_dimensions(file)!=expected:
            raise RuntimeError("Local media failed dimensions QC: "+str(file))
    for url in urls(obj):
        for trial in range(16):
            try:
                with urllib.request.urlopen(urllib.request.Request(url,method="HEAD"),timeout=12) as resp:
                    if resp.status==200: break
            except Exception: pass
            time.sleep(6)
        else:
            raise RuntimeError("Public approved media unavailable: "+url)
    print("Public URLs and full-frame pixel dimensions verified")

def gql(key, query, variables=None):
    body=json.dumps({"query":query,"variables":variables or {}}).encode()
    req=urllib.request.Request(BUFFER_ENDPOINT,data=body,method="POST",
      headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=45) as response:
        data=json.load(response)
    if data.get("errors"):
        raise RuntimeError("Buffer API returned GraphQL errors: "+str(data["errors"])[:650])
    return data.get("data") or {}

def channels(key):
    organizations=(gql(key,"query { account { organizations { id name } } }").get("account") or {}).get("organizations") or []
    found={"instagram":[],"tiktok":[],"youtube":[]}
    for org in organizations:
        data=gql(key,"query ($id: OrganizationId!) { channels(input: { organizationId: $id }) { id name service } }",{"id":org["id"]})
        for ch in data.get("channels") or []:
            service=str(ch.get("service","")).lower()
            if service in found:
                found[service].append(ch["id"])
    if any(len(v)!=1 for v in found.values()):
        raise ValueError("Expected 1 Instagram, 1 TikTok and 1 YouTube channel; found: "+str({k:len(v) for k,v in found.items()}))
    return {k:v[0] for k,v in found.items()}

def write_receipt(obj, state):
    RECEIPTS.mkdir(exist_ok=True)
    name=RECEIPTS/(obj["approval_id"]+".json")
    name.write_text(json.dumps(state,indent=2)+"\n")
    execute("git","config","user.email","41898282+github-actions[bot]@users.noreply.github.com")
    execute("git","config","user.name","github-actions[bot]")
    execute("git","add",str(name.relative_to(ROOT)))
    if subprocess.run(["git","diff","--cached","--quiet"],cwd=ROOT).returncode:
        execute("git","commit","-m","Record BLCKPEAK post attempt")
        execute("git","push")

def enforce_daily_post_cap(obj, state):
    """Limit to two distinct approved creatives per SCHEDULED Chicago day."""
    day=scheduled_at(obj).astimezone(ZoneInfo("America/Chicago")).date().isoformat()
    already=state.get("scheduled_post_day")
    if already:
        if already!=day:
            raise ValueError("Cannot reschedule a creative after a publishing attempt")
        return state
    previous=0
    if RECEIPTS.exists():
        for other in RECEIPTS.glob("*.json"):
            if other.stem==obj["approval_id"]: continue
            try:
                row=json.loads(other.read_text())
                if row.get("attempts") and (row.get("scheduled_post_day") or row.get("local_post_day"))==day:
                    previous+=1
            except (ValueError, OSError): continue
    if previous>=2:
        raise RuntimeError("Two-post daily cap reached for scheduled date "+day+" (America/Chicago). Approval remains pending.")
    state["scheduled_post_day"]=day
    return state

def publish(obj):
    if os.getenv("PUBLISHING_ENABLED")!="true":
        raise ValueError("Owner has not enabled organic publishing")
    if obj.get("audio_policy") != "silent_explicitly_approved":
        raise ValueError("Silent automatic post not explicitly accepted; native TikTok/Instagram music requires manual platform finishing, or separately licensed approved audio")
    due=due_at_utc(obj)  # Preflight before any external write
    key=os.getenv("BUFFER_API_KEY")
    if not key: raise ValueError("Missing encrypted Buffer API secret")
    ids=channels(key)
    mp4,instagram,tiktok=urls(obj)
    verify(obj)
    file=RECEIPTS/(obj["approval_id"]+".json")
    state=json.loads(file.read_text()) if file.exists() else {"approval_id":obj["approval_id"],"attempts":{}}
    state=enforce_daily_post_cap(obj,state)
    mutation="mutation($input: CreatePostInput!) { createPost(input: $input) { ... on PostActionSuccess { post { id status dueAt } } ... on MutationError { message } } }"
    for service in ("instagram","tiktok","youtube"):
        if service in state["attempts"]:
            print("Skipping previously attempted",service); continue
        # Persist before external request: no unsafe retries after unknown API results.
        state["attempts"][service]={"status":"attempting"}
        write_receipt(obj,state)
        if service=="instagram":
            assets=[{"image":{"url":instagram,"metadata":{"altText":"BLCKPEAK handheld showerhead"}}}]
            meta={"instagram":{"type":"post","shouldShareToFeed":True,"isAiGenerated":True}}
        elif service=="tiktok":
            assets=[{"image":{"url":tiktok,"metadata":{"altText":"BLCKPEAK handheld showerhead"}}}]
            meta={"tiktok":{"title":obj["youtube_title"][:80]}}
        else:
            assets=[{"video":{"url":mp4,"metadata":{"title":obj["youtube_title"]}}}]
            meta={"youtube":{"categoryId":"26","title":obj["youtube_title"],"madeForKids":False,"isAiGenerated":True}}
        inp={"channelId":ids[service],"text":obj["caption_"+service],
             "assets":assets,"metadata":meta,"mode":"customScheduled","dueAt":due,
             "schedulingType":"automatic","needsApproval":False,
             "saveToDraft":False,"aiAssisted":True}
        try:
            response=gql(key,mutation,{"input":inp}).get("createPost") or {}
            post=response.get("post") or {}
            if not post.get("id"):
                raise RuntimeError("Buffer did not accept scheduled post: "+str(response)[:400])
            returned=post.get("dueAt")
            if not returned or abs((datetime.fromisoformat(returned.replace("Z","+00:00"))-scheduled_at(obj)).total_seconds())>5:
                raise RuntimeError("Buffer returned missing or incorrect scheduled time; check the post ID before retrying")
            status=str(post.get("status") or "").lower()
            if status in ("sent","published"):
                raise RuntimeError("Buffer reported immediate publishing rather than scheduling")
            state["attempts"][service]={"status":"buffer_scheduled","id":post["id"],"buffer_status":post.get("status"),"due_at":returned}
        except Exception as err:
            state["attempts"][service]={"status":"uncertain","error":str(err)[:500]}
        write_receipt(obj,state)
    print(json.dumps(state,indent=2))
    if any((state["attempts"].get(s) or {}).get("status")!="buffer_scheduled" for s in ("instagram","tiktok","youtube")):
        raise RuntimeError("Some channels require review in Buffer Calendar; DO NOT retry automatically")

if __name__=="__main__":
    item=approval()
    if len(sys.argv)!=2: raise SystemExit("Use prepare, verify or publish")
    op=sys.argv[1]
    if op=="prepare":prepare(item)
    elif op=="verify":verify(item)
    elif op=="publish":publish(item)
    else:raise SystemExit("Invalid operation")
