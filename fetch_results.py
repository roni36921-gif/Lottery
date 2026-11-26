
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["LOTTERY_API_KEY"]
RESULT_FILE = "results.json"

today = datetime.now(ZoneInfo("Asia/Kolkata"))
date_text = today.strftime("%d-%m-%Y")

# Current scheduled slot
hour = today.hour

if hour < 15:
    slot = "1pm"
elif hour < 19:
    slot = "6pm"
else:
    slot = "8pm"

# Load existing results
if os.path.exists(RESULT_FILE):
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception:
        results = {}
else:
    results = {}

# Reset only when the date changes
if results.get("date") != date_text:
    results = {"date": date_text, "results": {}}

results.setdefault("results", {})

old_result = results["results"].get(slot)

def is_published(item):
    if not isinstance(item, dict) or not item.get("success"):
        return False

    data = item.get("data") or {}

    if data.get("status") == "upcoming":
        return False

    return bool(
        data.get("first")
        or data.get("prizes")
        or data.get("files")
    )

params = urllib.parse.urlencode({
    "date": date_text,
    "slot": slot,
    "access-token": TOKEN
})

url = "https://api.sambad.com/v2/dear/result?" + params

try:
    request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=30) as response:
        new_result = json.loads(response.read())

    # Do not replace an already published result with upcoming data
    if (
        is_published(old_result)
        and new_result.get("success")
        and (new_result.get("data") or {}).get("status") == "upcoming"
    ):
        print(f"{slot}: Keeping previous published result")

    elif new_result.get("success"):
        results["results"][slot] = new_result
        print(f"{slot}: API response saved")

    else:
        print(f"{slot}: API did not return success")

except Exception as error:
    print(f"{slot}: API error: {error}")

    # Keep previous successful result if available
    if old_result is None:
        results["results"][slot] = {"error": str(error)}

with open(RESULT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Lottery results update completed!")
        
