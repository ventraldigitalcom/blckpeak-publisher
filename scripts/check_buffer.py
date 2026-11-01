#!/usr/bin/env python3
"""Read-only Buffer authorization and channel check. No post creation or content changes."""
import json
import os
import urllib.request

TOKEN = os.environ.get("BUFFER_API_KEY")
if not TOKEN:
    raise SystemExit("FAILED: BUFFER_API_KEY is missing from GitHub Actions repository secrets")

def query(q, variables=None):
    req = urllib.request.Request(
        "https://api.buffer.com",
        data=json.dumps({"query":q,"variables":variables or {}}).encode(),
        headers={"Authorization":"Bearer "+TOKEN, "Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result=json.load(resp)
    except Exception as exc:
        raise SystemExit("FAILED: Buffer API authentication/network check: "+type(exc).__name__)
    if result.get("errors"):
        # Avoid logging potentially sensitive response data.
        raise SystemExit("FAILED: Buffer rejected a read-only GraphQL query. Check key permissions and validity.")
    return result.get("data") or {}

organizations=(query("query { account { organizations { id } } }").get("account") or {}).get("organizations") or []
channels={"instagram":[],"tiktok":[],"youtube":[]}
for org in organizations:
    fetched=query("query ($id: OrganizationId!) { channels(input: {organizationId:$id}) { id service isDisconnected isLocked } }",{"id":org["id"]})
    for ch in fetched.get("channels") or []:
        k=ch.get("service")
        if k in channels:channels[k].append(ch)
for name, matches in channels.items():
    if len(matches)!=1:
        raise SystemExit("FAILED: "+name+" requires exactly one connected channel (found "+str(len(matches))+").")
    if matches[0].get("isDisconnected") or matches[0].get("isLocked"):
        raise SystemExit("FAILED: "+name+" is disconnected or locked in Buffer.")
    print("PASS:",name,"channel is connected and unlocked.")
print("PASS: Buffer key and three channels can be read. No posts were sent.")
print("NOTE: Successful read-only test does not verify posting permissions or automatic publishing rights.")
