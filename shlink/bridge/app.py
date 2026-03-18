import time
import os
import requests
from uptime_kuma_api import UptimeKumaApi, MonitorType

SHLINK_API_URL = os.getenv("SHLINK_API_URL", "http://shlink:8080")
SHLINK_API_KEY = os.getenv("SHLINK_API_KEY")
KUMA_URL = os.getenv("KUMA_URL", "http://uptime_kuma:3001")
KUMA_USER = os.getenv("KUMA_USER")
KUMA_PASS = os.getenv("KUMA_PASS")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))


def get_shlink_urls():
    headers = {"X-Api-Key": SHLINK_API_KEY}
    result = []
    page = 1
    while True:
        resp = requests.get(
            f"{SHLINK_API_URL}/rest/v3/short-urls",
            headers=headers,
            params={"itemsPerPage": 100, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()["shortUrls"]
        result.extend(data["data"])
        if page >= data["pagination"]["pagesCount"]:
            break
        page += 1
    return result


def get_monitored_urls(api):
    monitors = api.get_monitors()
    return {m["url"] for m in monitors if m.get("url")}


def main():
    print(f"Bridge started — polling every {POLL_INTERVAL}s")
    while True:
        try:
            urls = get_shlink_urls()
            with UptimeKumaApi(KUMA_URL) as api:
                api.login(KUMA_USER, KUMA_PASS)
                monitored = get_monitored_urls(api)

                for url in urls:
                    long_url = url["longUrl"]
                    short_code = url["shortCode"]

                    if long_url not in monitored:
                        api.add_monitor(
                            type=MonitorType.HTTP,
                            name=f"[{short_code}] {long_url[:80]}",
                            url=long_url,
                            interval=300,
                        )
                        print(f"[+] Added monitor: {short_code} → {long_url}")

        except Exception as e:
            print(f"[!] Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
