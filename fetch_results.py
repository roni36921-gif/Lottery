
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["LOTTERY_API_KEY"]
RESULT_FILE = "results.json"
API_URL = "https://api.sambad.com/v2/dear/result"

now = datetime.now(ZoneInfo("Asia/Kolkata"))
today = now.strftime("%d-%m-%Y")

SLOTS = ["1pm", "6pm", "8pm"]


def load_results():
    if os.path.exists(RESULT_FILE):
        try:
            with open(RESULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as error:
            print("JSON load error:", error)

    return {}


def has_image(item):
    if not isinstance(item, dict) or not item.get("success"):
        return False

    data = item.get("data") or {}
    files = data.get("files") or {}

    return (
        data.get("status") != "upcoming"
        and isinstance(files, dict)
        and bool(files.get("jpg"))
    )


def fetch_slot(slot):
    params = urllib.parse.urlencode({
        "date": today,
        "slot": slot,
        "access-token": TOKEN
    })

    request = urllib.request.Request(
        API_URL + "?" + params,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if not isinstance(result, dict):
        raise ValueError("Invalid API response")

    return result


results = load_results()

if not isinstance(results.get("history"), dict):
    results["history"] = {}

if not isinstance(results.get("results"), dict):
    results["results"] = {}

history = results["history"]
current = results["results"]

# Archive old published images before starting a new date.
old_date = results.get("date")

if old_date and old_date != today:
    old_items = current.copy()

    for slot, item in old_items.items():
        if slot in SLOTS and has_image(item):
            history.setdefault(old_date, {})
            history[old_date][slot] = item

    current = {}
    results["results"] = current

# Fetch all three slots without deleting saved images on errors.
for slot in SLOTS:
    old_item = current.get(slot)

    try:
        new_item = fetch_slot(slot)

        if has_image(new_item):
            current[slot] = new_item
            print(slot, "New result image saved")

        elif has_image(old_item):
            print(slot, "Keeping existing image")

        elif new_item.get("success"):
            current[slot] = new_item
            print(slot, "No published image yet")

        else:
            print(slot, "API did not return success")

    except Exception as error:
        print(slot, "API error:", error)

        # Keep the existing result if the API fails.
        if old_item is None:
            current[slot] = {"error": str(error)}

results["date"] = today
results["results"] = current
results["history"] = history

with open(RESULT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("All three slots checked.")
