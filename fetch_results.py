
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

from datetime import datetime
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


TOKEN = os.environ["LOTTERY_API_KEY"]
RESULT_FILE = "results.json"
API_URL = "https://api.sambad.com/v2/dear/result"

SLOTS = ["1pm", "6pm", "8pm"]
IST = ZoneInfo("Asia/Kolkata")

MAX_RETRIES = 3
REQUEST_DELAY = 3


now = datetime.now(IST)
today = now.strftime("%d-%m-%Y")


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


def get_image_url(files):
    if not isinstance(files, dict):
        return ""

    for key, value in files.items():
        if not isinstance(value, str):
            continue

        url = value.strip()

        try:
            parsed = urlparse(url)

            if parsed.scheme not in ("http", "https"):
                continue

            extension = os.path.splitext(parsed.path)[1].lower()

            if extension in (".jpg", ".jpeg", ".png", ".webp"):
                return url

            if str(key).lower() in (
                "jpg", "jpeg", "png", "webp", "image"
            ):
                return url

        except Exception:
            continue

    return ""


def normalize_item(item):
    if not isinstance(item, dict):
        return item

    item = item.copy()
    data = item.get("data")

    if not isinstance(data, dict):
        return item

    data = data.copy()
    files = data.get("files") or {}

    if isinstance(files, dict):
        files = files.copy()
        image_url = get_image_url(files)

        if image_url:
            # Keep compatibility with the existing HTML.
            files["jpg"] = image_url

        data["files"] = files

    item["data"] = data
    return item


def has_image(item):
    if not isinstance(item, dict):
        return False

    if item.get("success") is not True:
        return False

    data = item.get("data") or {}

    if str(data.get("status", "")).lower() == "upcoming":
        return False

    return bool(get_image_url(data.get("files") or {}))


def retry_delay(error, attempt):
    if isinstance(error, urllib.error.HTTPError):
        retry_after = error.headers.get("Retry-After")

        if retry_after:
            try:
                return min(120, max(1, int(retry_after)))
            except ValueError:
                try:
                    target = parsedate_to_datetime(retry_after)
                    seconds = (
                        target - datetime.now(target.tzinfo)
                    ).total_seconds()
                    return min(120, max(1, int(seconds)))
                except Exception:
                    pass

    return min(60, 5 * (2 ** attempt))


def fetch_slot(slot):
    params = urllib.parse.urlencode({
        "date": today,
        "slot": slot,
        "access-token": TOKEN
    })

    request = urllib.request.Request(
        API_URL + "?" + params,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    )

    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(
                request, timeout=30
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            if not isinstance(result, dict):
                raise ValueError("Invalid API response")

            return normalize_item(result)

        except urllib.error.HTTPError as error:
            if error.code != 429 and error.code < 500:
                raise

            if attempt == MAX_RETRIES - 1:
                raise

            delay = retry_delay(error, attempt)
            print(
                slot, "HTTP", error.code,
                "- retrying after", delay, "seconds"
            )
            time.sleep(delay)

        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise

            delay = retry_delay(error, attempt)
            print(
                slot, "Network error - retrying after",
                delay, "seconds"
            )
            time.sleep(delay)

    raise RuntimeError("API retries exhausted")


# Load existing data
results = load_results()

if not isinstance(results.get("history"), dict):
    results["history"] = {}

if not isinstance(results.get("results"), dict):
    results["results"] = {}

history = results["history"]
current = results["results"]

# Archive previous date's published results
old_date = results.get("date")

if old_date and old_date != today:
    for slot, item in current.items():
        if slot in SLOTS and has_image(item):
            history.setdefault(old_date, {})
            history[old_date][slot] = item

    current = {}
    results["results"] = current


# Fetch slots one by one
for index, slot in enumerate(SLOTS):

    old_item = current.get(slot)

    try:
        new_item = fetch_slot(slot)

        if has_image(new_item):
            current[slot] = new_item
            print(slot, "Published result image saved")

        elif has_image(old_item):
            print(slot, "Keeping previous published result")

        elif new_item.get("success"):
            current[slot] = new_item
            print(slot, "Waiting for published result")

        else:
            print(slot, "API returned unsuccessful response")

    except Exception as error:
        print(slot, "API error:", str(error))

        if old_item is None:
            current[slot] = {
                "success": False,
                "error": str(error)
            }

    # Avoid sending requests too quickly
    if index < len(SLOTS) - 1:
        time.sleep(REQUEST_DELAY)


# Save JSON
results["date"] = today
results["results"] = current
results["history"] = history

with open(RESULT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        results,
        f,
        indent=2,
        ensure_ascii=False
    )

print("All three slots checked successfully.")
print("Date:", today)
