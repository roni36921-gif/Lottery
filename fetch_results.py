
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

# Select current scheduled slot
hour = today.hour

if hour < 15:
    slot = "1pm"
elif hour < 19:
    slot = "6pm"
else:
    slot = "8pm"

# Load existing results WITHOUT deleting previous dates' results
if os.path.exists(RESULT_FILE):
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception:
        results = {}
else:
    results = {}

results.setdefault("results", {})

# Keep previous published result for this slot
old_result = results["results"].get(slot)


def is_published(item):
    if not isinstance(item, dict):
        return False

    if not item.get("success"):
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
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        new_result = json.loads(response.read())

    if not isinstance(new_result, dict):
        raise ValueError("Invalid API response")

    if is_published(new_result):
        # New published result replaces previous result
        results["results"][slot] = new_result
        print(f"{slot}: New published result saved")

    elif is_published(old_result):
        # Keep old image and result until new result is published
        print(f"{slot}: Keeping previous published result")

    elif new_result.get("success"):
        # No previous published result; save upcoming data
        results["results"][slot] = new_result
        print(f"{slot}: Upcoming result saved")

    else:
        print(f"{slot}: API did not return success")

except Exception as error:
    print(f"{slot}: API error: {error}")

    # Never delete previous published result on API error
    if old_result is None:
        results["results"][slot] = {
            "error": str(error)
        }

# Update current date, but preserve previous results
results["date"] = date_text

# Save JSON
with open(RESULT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Automatic lottery result update completed!")
