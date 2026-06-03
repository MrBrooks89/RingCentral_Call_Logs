# Project Overview

This project provides a set of Python scripts for interacting with the RingCentral API. It allows users to programmatically make outbound calls and retrieve detailed call logs.

The project uses the RingCentral Python SDK and relies on environment variables for configuration.

## Key Files

*   `fetch_call_logs_by_date.py`: This script fetches and displays detailed call logs from the last 30 days, including information about call legs and recordings. **Note: This script is configured to only retrieve call logs that have associated recordings.**
*   `search_call_logs_by_phone.py`: This script fetches and displays call logs filtered by a specific phone number and date range. This script does NOT include call recordings.
*   `delete_call_logs_by_date.py`: This script deletes call logs based on specified criteria. **Note: This script is configured to only delete call logs that have associated recordings.**
*   `delete_recent_call_logs.py`: This script deletes call logs from the last 30 days. **Note: This script is configured to only delete call logs that have associated recordings.**

## Building and Running

### Prerequisites

*   Python 3
*   RingCentral Python SDK (`pip install ringcentral`)

### Configuration

The following environment variables must be set to authenticate with the RingCentral API:

*   `RC_CLIENT_ID`: Your RingCentral application client ID.
*   `RC_CLIENT_SECRET`: Your RingCentral application client secret.
*   `RC_JWT_TOKEN`: Your RingCentral JWT token.
*   `RC_SERVER`: The RingCentral server URL (e.g., `https://platform.ringcentral.com`).

### Running the Scripts


*   **To fetch call logs:**

    ```bash
    python fetch_call_logs_by_date.py [--date_from YYYY-MM-DDTHH:MM:SS.sssZ] [--date_to YYYY-MM-DDTHH:MM:SS.sssZ]
    ```

    *   `--date_from`: The start date for the call logs in ISO 8601 format. Defaults to 30 days ago.
    *   `--date_to`: The end date for the call logs in ISO 8601 format. Defaults to the current time.

*   **To search call logs by phone number:**

    ```bash
    python search_call_logs_by_phone.py --phone_number PHONE_NUMBER [--date_from YYYY-MM-DDTHH:MM:SS.sssZ] [--date_to YYYY-MM-DDTHH:MM:SS.sssZ]
    ```

    *   `--phone_number`: The phone number to filter call logs for (required).
    *   `--date_from`: The start date for the call logs in ISO 8601 format. Defaults to 30 days ago.
    *   `--date_to`: The end date for the call logs in ISO 8601 format. Defaults to the current time.

*   **To delete call logs:**

    ```bash
    python delete_call_logs_by_date.py --phone_number PHONE_NUMBER [--date_from YYYY-MM-DDTHH:MM:SS.sssZ] [--date_to YYYY-MM-DDTHH:MM:SS.sssZ]
    ```

    *   `--phone_number`: The phone number to filter call logs for (required).
    *   `--date_from`: The start date for the call logs in ISO 8601 format. Defaults to 24 hours ago.
    *   `--date_to`: The end date for the call logs in ISO 8601 format. Defaults to the current time.

*   **To delete recent call logs (last 30 days):**

    ```bash
    python delete_recent_call_logs.py
    ```

## Development Conventions

*   The project uses standard Python conventions.
*   Sensitive information, such as API credentials, is managed through environment variables and should not be hard-coded in the source files.
*   The `fetch_call_logs_by_date.py`, `search_call_logs_by_phone.py` and `delete_call_logs_by_date.py` script includes a basic rate limiter to avoid exceeding the RingCentral API's request limits.

## References

*   **RingCentral Call Log API Guide:** https://developers.ringcentral.com/guide/voice/call-log/api
*   **RingCentral Call Log API Reference:** https://developers.ringcentral.com/api-reference/Call-Log/readUserCallLog
*   **RingCentral Delete User Call Log API Reference:** https://developers.ringcentral.com/api-reference/Call-Log/deleteUserCallLog
