
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["LOTTERY_API_KEY"]
RESULT_FILE = "results.json"
IST = ZoneInfo("Asia/Kolkata")

today = datetime.now(IST)
date_text = today.strftime("%d-%m-%Y")


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


def get_result_date(item, fallback_date):
    if isinstance(item, dict):
        data = item.get("data") or {}
        return data.get("date") or fallback_date
    return fallback_date


# Select the scheduled slot
hour = today.hour

if hour < 15:
    slot = "1pm"
elif hour < 19:
    slot = "6pm"
else:
    slot = "8pm"


# Load existing JSON
if os.path.exists(RESULT_FILE):
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except Exception:
        results = {}
else:
    results = {}

if not isinstance(results, dict):
    results = {}

if not isinstance(results.get("results"), dict):
    results["results"] = {}

if not isinstance(results.get("history"), dict):
    results["history"] = {}


# Archive existing results before changing the date
previous_date = results.get("date")

for old_slot, old_item in list(results["results"].items()):
    if not is_published(old_item):
        continue

    archive_date = get_result_date(old_item, previous_date)

    if archive_date:
        results["history"].setdefault(archive_date, {})
        results["history"][archive_date][old_slot] = old_item


# If date changed, start a fresh current-day result list
if previous_date != date_text:
    results["results"] = {}


# Keep today's previous published result
old_result = results["results"].get(slot)


# Prepare API request
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

        # Save today's published result
        results["results"][slot] = new_result

        # Also save a permanent date-wise history copy
        results["history"].setdefault(date_text, {})
        results["history"][date_text][slot] = new_result

        print(f"{slot}: Published result saved in current and history")

    elif is_published(old_result):

        # Never replace a published result with upcoming data
        print(f"{slot}: Keeping today's previous published result")

    elif new_result.get("success"):

        # Save upcoming data for today's slot
        results["results"][slot] = new_result

        print(f"{slot}: Upcoming result saved")

    else:
        print(f"{slot}: API did not return success")


except Exception as error:
    print(f"{slot}: API error: {error}")

    # Keep existing published data safe
    if is_published(old_result):
        print(f"{slot}: Previous published result preserved")


# Update current date
results["date"] = date_text


# Save JSON safely
temp_file = RESULT_FILE + ".tmp"

with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

os.replace(temp_file, RESULT_FILE)

print("Automatic lottery result update completed!")
print("Current date:", date_text)
print("Updated slot:", slot)
print("History dates:", len(results["history"]))
