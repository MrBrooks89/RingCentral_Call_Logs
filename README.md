# RingCentral Call Logs Management

This repository contains a set of Python scripts designed for interacting with the RingCentral API to manage call logs. It provides functionalities to fetch and delete call logs, enabling programmatic control over your RingCentral call history.

## Key Features

*   **Fetch Call Logs**: Retrieve detailed call logs, including information about call legs and recordings, for specified date ranges.
*   **Delete Call Logs**: Remove call logs based on various criteria, such as date range.
*   **Easy Configuration**: Utilizes environment variables for secure API credential management.

## Key Files and Their Functions

*   `fetch_call_logs_by_date.py`: Fetches and displays detailed call logs from your RingCentral account. By default, it retrieves logs from the last 30 days, but you can specify custom date ranges.
*   `delete_call_logs_by_date.py`: Deletes call logs that match an optional date range.
*   `delete_recent_call_logs.py`: Conveniently deletes all call logs from the last 30 days.

## Getting Started

### Prerequisites

Ensure you have the following installed:

*   **Python 3**: The scripts are written in Python 3.
*   **RingCentral Python SDK**: Install it using pip:
    ```bash
    pip install ringcentral
    ```

### Configuration

To authenticate with the RingCentral API, you must set the following environment variables. It's recommended to add these to your `.bashrc`, `.zshrc`, or equivalent shell configuration file, or set them before running the scripts.

*   `RC_CLIENT_ID`: Your RingCentral application client ID.
*   `RC_CLIENT_SECRET`: Your RingCentral application client secret.
*   `RC_JWT_TOKEN`: Your RingCentral JWT (JSON Web Token) for authentication.
*   `RC_SERVER`: The RingCentral API server URL (e.g., `https://platform.ringcentral.com` for production or `https://platform.devtest.ringcentral.com` for sandbox).

### Running the Scripts

Navigate to the project directory in your terminal.

#### Fetching Call Logs

To fetch call logs, you can use `fetch_call_logs_by_date.py`:

```bash
python fetch_call_logs_by_date.py [--date_from YYYY-MM-DDTHH:MM:SS.sssZ] [--date_to YYYY-MM-DDTHH:MM:SS.sssZ]
```

*   `--date_from`: (Optional) The start date for the call logs in ISO 8601 format (e.g., `2023-01-01T00:00:00.000Z`). Defaults to 30 days ago.
*   `--date_to`: (Optional) The end date for the call logs in ISO 8601 format. Defaults to the current time.

**Example: Fetching logs from a specific period**
```bash
python fetch_call_logs_by_date.py --date_from 2023-10-01T00:00:00.000Z --date_to 2023-10-31T23:59:59.999Z
```

#### Deleting Call Logs by Date Range

To delete specific call logs, use `delete_call_logs_by_date.py`:

```bash
python delete_call_logs_by_date.py [--date_from YYYY-MM-DDTHH:MM:SS.sssZ] [--date_to YYYY-MM-DDTHH:MM:SS.sssZ]
```

*   `--date_from`: (Optional) The start date for the call logs in ISO 8601 format. Defaults to 24 hours ago.
*   `--date_to`: (Optional) The end date for the call logs in ISO 8601 format. Defaults to the current time.

**Example: Deleting logs from the last 24 hours**
```bash
python delete_call_logs_by_date.py
```

**Example: Deleting logs within a specific date range**
```bash
python delete_call_logs_by_date.py --date_from 2023-11-01T00:00:00.000Z --date_to 2023-11-07T23:59:59.999Z
```

#### Deleting Recent Call Logs

To delete all call logs from the last 30 days, use `delete_recent_call_logs.py`:

```bash
python delete_recent_call_logs.py
```

## Development Conventions

*   **Python Standards**: Adheres to standard Python coding conventions.
*   **Environment Variables**: Sensitive information (API credentials) is managed via environment variables and should never be hard-coded.
*   **Rate Limiting**: `fetch_call_logs_by_date.py` and `delete_call_logs_by_date.py` include basic rate limiting to prevent exceeding RingCentral API request limits.

## References

For more detailed information on the RingCentral API, refer to:

*   **RingCentral Call Log API Guide:** [https://developers.ringcentral.com/guide/voice/call-log/api](https://developers.ringcentral.com/guide/voice/call-log/api)
*   **RingCentral Call Log API Reference:** [https://developers.ringcentral.com/api-reference/Call-Log/readUserCallLog](https://developers.ringcentral.com/api-reference/Call-Log/readUserCallLog)
*   **RingCentral Delete User Call Log API Reference:** [https://developers.ringcentral.com/api-reference/Call-Log/deleteUserCallLog](https://developers.ringcentral.com/api-reference/Call-Log/deleteUserCallLog)