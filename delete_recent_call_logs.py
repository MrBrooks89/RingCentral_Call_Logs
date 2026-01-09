import os
import sys
import argparse
import time
from collections import deque
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
try:
    platform.login(jwt=JWT_TOKEN)
except Exception as e:
    sys.exit("Unable to authenticate to platform: " + str(e))

# ---------------------- ARGPARSE ----------------------
parser = argparse.ArgumentParser(
    description="Delete RingCentral call logs older than 30 days."
)
# parser.add_argument(
#     "--phone_number",
#     required=True,
#     help="Phone number to filter call logs for.",
# )
args = parser.parse_args()

# ---------------------- DATE RANGE ----------------------
# We want to delete call logs older than 30 days.
# So we set the date_to to 30 days ago.
# date_from is omitted to get everything up to date_to.
now_utc = datetime.now(timezone.utc)
date_to = (
    (now_utc - timedelta(days=30))
    .isoformat(timespec="milliseconds")
    .replace("+00:00", "Z")
)


# ---------------------- HELPERS ----------------------
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


def _platform_delete_with_throttle(url_or_path, max_retries=3):
    """
    Throttled DELETE with basic 429 handling.
    Respects Retry-After header when present; defaults to 60s if absent.
    """
    attempt = 0
    while True:
        _rate_limit_wait()
        try:
            resp = platform.delete(url_or_path)
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


# ---------------------- LOGGING ----------------------
LOG_FILE_NAME = "deleted_call_logs.log"


def log_deleted_record(record, log_file):
    try:
        call_log_id = getattr(
            record,
            "id",
            record.get("id") if isinstance(record, dict) else None,
        )
        start_time = getattr(
            record,
            "startTime",
            record.get("startTime") if isinstance(record, dict) else None,
        )
        direction = getattr(
            record,
            "direction",
            record.get("direction") if isinstance(record, dict) else None,
        )
        from_phone = (
            getattr(record, "from", {}).get("phoneNumber")
            if isinstance(record, dict)
            else getattr(getattr(record, "from", None), "phoneNumber", None)
        )
        to_phone = (
            getattr(record, "to", {}).get("phoneNumber")
            if isinstance(record, dict)
            else getattr(getattr(record, "to", None), "phoneNumber", None)
        )

        log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
        log_file.write(f"Deleted Call Log ID: {call_log_id}\n")
        log_file.write(f"Start Time: {start_time}\n")
        log_file.write(f"Direction: {direction}\n")
        log_file.write(f"From: {from_phone}\n")
        log_file.write(f"To: {to_phone}\n")
        log_file.write("-" * 30 + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")


# ---------------------- FETCH CALL LOG ----------------------


all_records = []


page = 1


try:


    while True:


        params = {


            "view": "Simple",


            "dateFrom": "2025-10-13T00:00:00.000Z", # Explicitly set start date as requested


            "dateTo": date_to,


            "recordingType": "All",


            "perPage": 250,


            "page": page,


        }


        print(f"Fetching page {page} with dateFrom={params['dateFrom']} and dateTo={params['dateTo']}...")


        


        api_response = _platform_get_with_throttle(


            "/restapi/v1.0/account/~/call-log", params


        )


        json_response = api_response.json()





        # If the records list is empty, we've reached the end


        if not json_response.records:


            print("Found no more records. Concluding fetch.")


            break





        all_records.extend(json_response.records)


        page += 1


except Exception as e:


    sys.exit(f"An error occurred during call log fetching: {e}")

records = all_records  # Use the comprehensive list for deletion


if not records:
    print(f"No call logs found older than {date_to}.")
    sys.exit(0)

# ---------------------- DELETE CALL LOG ----------------------
with open(LOG_FILE_NAME, "a") as log_file:
    for record in records:
        print("--------- Call Log Record ---------")
        call_log_id = getattr(
            record,
            "id",
            record.get("id") if isinstance(record, dict) else None,
        )
        print(f"id: {call_log_id}")
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

        to_obj = getattr(
            record,
            "to",
            record.get("to") if isinstance(record, dict) else None,
        )
        from_obj = getattr(
            record,
            "from",
            record.get("from") if isinstance(record, dict) else None,
        )
        _print_party("to", to_obj)
        _print_party("from", from_obj)

        print(
            f"transport: {getattr(record, 'transport', record.get('transport') if isinstance(record, dict) else None)}"
        )
        print(
            f"lastModifiedTime: {getattr(record, 'lastModifiedTime', record.get('lastModifiedTime') if isinstance(record, dict) else None)}"
        )

        recording = getattr(
            record,
            "recording",
            record.get("recording") if isinstance(record, dict) else None,
        )
        _print_recording(recording)

        if not recording:
            print(f"Skipping call log {call_log_id} (no recording found).")
            print("-----------------------------------\n")
            continue  # Move to the next record

        print("-----------------------------------")

        if True:
            try:
                endpoint = f"/restapi/v1.0/account/~/call-log/{call_log_id}"
                resp = _platform_delete_with_throttle(endpoint)
                if resp.response().status_code == 204:
                    print(f"Successfully deleted call log with ID: {call_log_id}")
                    log_deleted_record(record, log_file)  # Log the deleted record
                else:
                    print(
                        f"Failed to delete call log with ID: {call_log_id}. Status code: {resp.response().status_code}"
                    )
            except Exception as e:
                print(f"An error occurred while deleting call log {call_log_id}: {e}")


        print("\n")

print("\nFinished processing call logs.")
