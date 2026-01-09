import os
import time
import zoneinfo
import argparse
from collections import deque
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from ringcentral import SDK

# ---------------------- ENV VARS ----------------------
CLIENT_ID = os.getenv("RC_CLIENT_ID")
CLIENT_SECRET = os.getenv("RC_CLIENT_SECRET")
JWT_TOKEN = os.getenv("RC_JWT_TOKEN")
SERVER_URL = os.getenv("RC_SERVER")

# ---------------------- SDK LOGIN ----------------------
rcsdk = SDK(CLIENT_ID, CLIENT_SECRET, SERVER_URL)
platform = rcsdk.platform()
platform.login(jwt=JWT_TOKEN)

# ---------------------- DATE RANGE (LAST 30 DAYS) ----------------------

now_utc = datetime.now(timezone.utc)
cutoff_utc = now_utc - timedelta(days=30)
date_to_default = cutoff_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")
date_from_default = "2025-11-01T00:00:00.000Z"

parser = argparse.ArgumentParser(description="Fetch RingCentral call logs.")
parser.add_argument(
    "--date_from",
    help="Start date for call logs (ISO 8601 format) Ex: 2025-11-01T00:00:00.000Z",
)
parser.add_argument(
    "--date_to",
    help="End date for call logs (ISO 8601 format) Ex: 2025-11-30T23:59:59.999Z",
)
args = parser.parse_args()

date_from = args.date_from if args.date_from else date_from_default
date_to = args.date_to if args.date_to else date_to_default


# ---------------------- FETCH CALL LOG ----------------------
params = {
    "perPage": 100,
    "page": 1,
    "view": "Simple",  # Simple or 'Detailed' if you want legs, billing, recording metadata
    "dateFrom": date_from,
    "dateTo": date_to,
    "recordingType": "All",  # Automatic or 'OnDemand' or 'All'
}

endpoint = "/restapi/v1.0/account/~/call-log"

# ---------------------- RATE LIMITER (10 req / 60s) ----------------------
REQUESTS_PER_WINDOW = 10
WINDOW_SECONDS = 60
_request_timestamps = deque()  # stores timestamps (epoch seconds) of recent requests


def _rate_limit_wait():
    """Block until we are under 10 requests / 60 seconds."""
    now = time.time()
    # Evict old timestamps outside the window
    while _request_timestamps and now - _request_timestamps[0] >= WINDOW_SECONDS:
        _request_timestamps.popleft()

    # If still at cap, wait until the oldest request falls out of the window
    if len(_request_timestamps) >= REQUESTS_PER_WINDOW:
        wait_sec = WINDOW_SECONDS - (now - _request_timestamps[0])
        if wait_sec > 0:
            time.sleep(wait_sec)


def _platform_get_with_throttle(url_or_path, params=None, max_retries=3):
    """
    Throttled GET with basic 429 handling.
    Respects Retry-After header when present; defaults to 60s if absent.
    """
    attempt = 0
    while True:
        _rate_limit_wait()
        try:
            resp = platform.get(url_or_path, params)
            _request_timestamps.append(time.time())  # record successful request time
            return resp
        except Exception as e:
            # Try to detect HTTP 429 and Retry-After header where available.
            retry_after_sec = None
            status_code = getattr(e, "status", None) or getattr(e, "code", None)

            headers = None
            # Some SDK versions expose the raw response via e.response
            if hasattr(e, "response") and e.response is not None:
                try:
                    headers = e.response.headers
                except Exception:
                    headers = None

            if status_code == 429:
                # Honor Retry-After if present, else default to 60s
                if headers:
                    ra = headers.get("Retry-After")
                    if ra:
                        try:
                            retry_after_sec = int(ra)
                        except ValueError:
                            retry_after_sec = 60
                if retry_after_sec is None:
                    retry_after_sec = 60

                time.sleep(retry_after_sec)
                attempt += 1
                if attempt <= max_retries:
                    continue
                else:
                    raise  # too many retries
            else:
                # Non-429 errors: small exponential backoff
                attempt += 1
                if attempt <= max_retries:
                    backoff = min(2**attempt, 30)
                    time.sleep(backoff)
                    continue
                raise


# ---------------------- HELPERS ----------------------
def _path_from_absolute_uri(absolute_uri: str) -> str:
    """Extract path+query if the SDK prefers relative URIs for follow-up calls."""
    parsed = urlparse(absolute_uri)
    return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path


def _print_party(label, party_obj):
    if not party_obj:
        print(f"{label}: None")
        return
    # Handle dict or SDK object
    if isinstance(party_obj, dict):
        phone = party_obj.get("phoneNumber")
        name = party_obj.get("name")
        location = party_obj.get("location")
    else:
        phone = getattr(party_obj, "phoneNumber", None)
        name = getattr(party_obj, "name", None)
        location = getattr(party_obj, "location", None)
    if location:
        print(f"{label}: {phone} ({name}) | location: {location}")
    else:
        print(f"{label}: {phone} ({name})")


def _print_recording(rec_obj):
    if not rec_obj:
        print("recording: None")
        return
    if isinstance(rec_obj, dict):
        rid = rec_obj.get("id")
        rtype = rec_obj.get("type")
        curi = rec_obj.get("contentUri")
    else:
        rid = getattr(rec_obj, "id", None)
        rtype = getattr(rec_obj, "type", None)
        curi = getattr(rec_obj, "contentUri", None)
    if curi:
        print(f"recording: id={rid}, type={rtype}, contentUri={curi}")
    else:
        print(f"recording: id={rid}, type={rtype}")


def _print_leg(i, leg):
    print(f"---- Leg {i} ----")
    g = (
        (lambda k: leg.get(k))
        if isinstance(leg, dict)
        else (lambda k: getattr(leg, k, None))
    )
    print(f"startTime: {g('startTime')}")
    print(f"duration: {g('duration')}")
    print(f"type: {g('type')}")
    print(f"direction: {g('direction')}")
    print(f"action: {g('action')}")
    print(f"result: {g('result')}")
    _print_party("to", g("to"))
    _print_party("from", g("from"))
    print(f"telephonySessionId: {g('telephonySessionId')}")
    print(f"transport: {g('transport')}")
    print(f"legType: {g('legType')}")
    ext = g("extension")
    if ext:
        if isinstance(ext, dict):
            ext_id = ext.get("id")
            ext_uri = ext.get("uri")
        else:
            ext_id = getattr(ext, "id", None)
            ext_uri = getattr(ext, "uri", None)
        print(f"extension: id={ext_id}, uri={ext_uri}")
    _print_recording(g("recording"))


# ---------------------- FIRST PAGE (THROTTLED) ----------------------
resp = _platform_get_with_throttle(endpoint, params)
data = resp.json()

# ---------------------- LOOP & PAGINATE ----------------------
while True:
    # records can be dicts; keep your getattr() style but fall back to dict values
    records = (
        data.get("records", [])
        if isinstance(data, dict)
        else getattr(data, "records", [])
    )
    for record in records:
        print("--------- Call Log Record ---------")
        print(
            f"id: {getattr(record, 'id', record.get('id') if isinstance(record, dict) else None)}"
        )
        print(
            f"uri: {getattr(record, 'uri', record.get('uri') if isinstance(record, dict) else None)}"
        )
        print(
            f"sessionId: {getattr(record, 'sessionId', record.get('sessionId') if isinstance(record, dict) else None)}"
        )
        print(
            f"startTime: {getattr(record, 'startTime', record.get('startTime') if isinstance(record, dict) else None)}"
        )
        print(
            f"duration: {getattr(record, 'duration', record.get('duration') if isinstance(record, dict) else None)}"
        )
        print(
            f"type: {getattr(record, 'type', record.get('type') if isinstance(record, dict) else None)}"
        )
        print(
            f"direction: {getattr(record, 'direction', record.get('direction') if isinstance(record, dict) else None)}"
        )
        print(
            f"action: {getattr(record, 'action', record.get('action') if isinstance(record, dict) else None)}"
        )
        print(
            f"result: {getattr(record, 'result', record.get('result') if isinstance(record, dict) else None)}"
        )

        # From and To numbers
        to_obj = getattr(
            record, "to", record.get("to") if isinstance(record, dict) else None
        )
        from_obj = getattr(
            record, "from", record.get("from") if isinstance(record, dict) else None
        )
        _print_party("to", to_obj)
        _print_party("from", from_obj)

        print(
            f"transport: {getattr(record, 'transport', record.get('transport') if isinstance(record, dict) else None)}"
        )
        print(
            f"lastModifiedTime: {getattr(record, 'lastModifiedTime', record.get('lastModifiedTime') if isinstance(record, dict) else None)}"
        )

        # Recording (only present if call has a recording)
        recording = getattr(
            record,
            "recording",
            record.get("recording") if isinstance(record, dict) else None,
        )
        _print_recording(recording)

        # Legs (only when view='Detailed')
        legs = getattr(
            record, "legs", record.get("legs") if isinstance(record, dict) else None
        )
        if legs:
            print(f"legs count: {len(legs)}")
            for i, leg in enumerate(legs, start=1):
                _print_leg(i, leg)
        else:
            print("legs: []")

        print("-----------------------------------\n")

    # pagination via navigation.nextPage
    navigation = (
        data.get("navigation", {})
        if isinstance(data, dict)
        else getattr(data, "navigation", {})
    )
    next_page = (
        navigation.get("nextPage", {})
        if isinstance(navigation, dict)
        else getattr(navigation, "nextPage", {})
    )
    next_uri = (
        next_page.get("uri")
        if isinstance(next_page, dict)
        else getattr(next_page, "uri", None)
    )

    if not next_uri:
        break  # no more pages

    next_path = _path_from_absolute_uri(next_uri)
    resp = _platform_get_with_throttle(next_path)
    data = resp.json()

print("\nFinished printing call log records.")
