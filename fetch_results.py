import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

token = os.environ["LOTTERY_API_KEY"]

today = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d-%m-%Y")

results = {"date": today, "results": {}}

for slot in ["1pm", "6pm", "8pm"]:
    params = urllib.parse.urlencode({
        "date": today,
        "slot": slot,
        "access-token": token
    })

    url = "https://api.sambad.com/v2/dear/result?" + params

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            results["results"][slot] = json.loads(response.read())
    except Exception as e:
        results["results"][slot] = {"error": str(e)}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Results updated")
