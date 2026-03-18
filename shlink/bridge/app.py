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

# Monitor names are prefixed so we can identify Shlink-managed monitors
NAME_PREFIX = "[shlink]"


def get_shlink_urls():
    """Returns dict: {shortCode: longUrl}"""
    headers = {"X-Api-Key": SHLINK_API_KEY}
    result = {}
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
        for item in data["data"]:
            result[item["shortCode"]] = item["longUrl"]
        if page >= data["pagination"]["pagesCount"]:
            break
        page += 1
    return result


def get_kuma_shlink_monitors(api):
    """Returns dict: {shortCode: {"id": int, "url": str}} for Shlink-managed monitors"""
    monitors = api.get_monitors()
    result = {}
    for m in monitors:
        name = m.get("name", "")
        if name.startswith(NAME_PREFIX):
            # Name format: "[shlink] shortCode | longUrl"
            try:
                rest = name[len(NAME_PREFIX):].strip()
                short_code = rest.split(" | ")[0]
                result[short_code] = {"id": m["id"], "url": m.get("url", "")}
            except Exception:
                continue
    return result


def monitor_name(short_code, long_url):
    return f"{NAME_PREFIX} {short_code} | {long_url[:80]}"


def sync(api, shlink_urls, kuma_monitors):
    shlink_codes = set(shlink_urls.keys())
    kuma_codes = set(kuma_monitors.keys())

    # ADD: in Shlink but not in Kuma
    for code in shlink_codes - kuma_codes:
        long_url = shlink_urls[code]
        api.add_monitor(
            type=MonitorType.HTTP,
            name=monitor_name(code, long_url),
            url=long_url,
            interval=300,
        )
        print(f"[+] Added:   {code} → {long_url}")

    # DELETE: in Kuma but not in Shlink
    for code in kuma_codes - shlink_codes:
        monitor_id = kuma_monitors[code]["id"]
        api.delete_monitor(monitor_id)
        print(f"[-] Deleted: {code} (removed from Shlink)")

    # UPDATE: in both but long URL changed
    for code in shlink_codes & kuma_codes:
        new_url = shlink_urls[code]
        old_url = kuma_monitors[code]["url"]
        if new_url != old_url:
            monitor_id = kuma_monitors[code]["id"]
            api.edit_monitor(
                id=monitor_id,
                name=monitor_name(code, new_url),
                url=new_url,
            )
            print(f"[~] Updated: {code} → {new_url}  (was: {old_url})")


def main():
    print(f"Bridge started — full sync every {POLL_INTERVAL}s")
    while True:
        try:
            shlink_urls = get_shlink_urls()
            with UptimeKumaApi(KUMA_URL) as api:
                api.login(KUMA_USER, KUMA_PASS)
                kuma_monitors = get_kuma_shlink_monitors(api)
                sync(api, shlink_urls, kuma_monitors)
        except Exception as e:
            print(f"[!] Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
