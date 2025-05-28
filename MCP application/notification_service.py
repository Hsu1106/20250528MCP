import sqlite3
import json
from datetime import datetime
import requests # Import requests

DATABASE_FILE = 'economic_events.db'

# TODO: Store this securely, e.g., in environment variables or a config file
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1375824641087766589/1iEZ8S3Bcse7fnPyXuWku2oMbDQzWO925hH0hGGYX6wfjeGYu2pWG09eIMShkbUldzFW" # Replace with your actual webhook URL

def get_latest_event_from_db():
    """Retrieves the latest event from the database."""
    conn = None
    latest_event = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Select the latest event based on timestamp
        cursor.execute("SELECT type, description, value, year, period, timestamp, source, series_id FROM events ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()

        if row:
            latest_event = {
                "type": row[0],
                "description": row[1],
                "value": row[2],
                "year": row[3],
                "period": row[4],
                "timestamp": row[5],
                "source": row[6],
                "series_id": row[7]
            }

    except sqlite3.Error as e:
        print(f"Database error while fetching latest event: {e}")
    finally:
        if conn:
            conn.close()

    return latest_event

def send_notification(event):
    """Sends a real-time notification for an economic event to Discord."""
    if not event:
        print("No event provided to send notification.")
        return

    print("\n--- Attempting to send notification to Discord ---")

    # Map series_id to Chinese and English names
    series_name_map = {
        'LNS14000000': 'Unemployment Rate (失業率)',
        'CES0000000001': 'Nonfarm Payroll (非農就業人數)',
        'CUUR0000SA0': 'CPI (All items) (消費者物價指數 - 所有項目)',
        'WPUID000000': 'PPI (All commodities) (生產者物價指數 - 所有商品)'
    }

    event_type = event.get('type', 'N/A')
    series_id = event.get('series_id', 'N/A')
    series_name = series_name_map.get(series_id, f'Unknown Series ({series_id})')
    value = event.get('value', 'N/A')
    year = event.get('year', 'N/A')
    period = event.get('period', 'N/A')
    timestamp = event.get('timestamp', 'N/A')
    source = event.get('source', 'N/A')
    # Get previous and expected values
    previous_value = event.get('previous_value', 'N/A') # Get previous value
    expected_value = event.get('expected_value', 'N/A') # Get expected value

    # Construct the Embed for Discord notification
    embed = {
        "title": "經濟事件提醒！ (Economic Event Alert!)", # Embed Title
        "description": f"Type (類型): {event_type}", # Add event type to description
        "color": 15258703, # Example color (a shade of orange), you can change this
        "fields": [ # Add fields for structured data
            {
                "name": "指標 (Indicator)",
                "value": series_name,
                "inline": True # Display fields inline if possible
            },
            {
                "name": "最新數值 (Latest Value)",
                "value": value,
                "inline": True
            },
             {
                "name": "前期值 (Previous Value)",
                "value": previous_value,
                "inline": True
            },
             {
                "name": "預期值 (Expected Value)",
                "value": expected_value,
                "inline": True
            },
            {
                 "name": "週期 (Period)",
                 "value": f"{year} {period}",
                 "inline": True
            },
            {
                "name": "來源 (Source)",
                "value": source,
                "inline": True
            }
            # You can add more fields as needed, e.g., link to source
        ],
        "timestamp": datetime.utcnow().isoformat() # Use UTC timestamp for consistency
        # You can also add a footer or author field if needed
    }

    # Construct the overall payload with the embed
    payload = {
        "embeds": [embed] # Embeds should be in a list
        # You can still add 'content' here for a message above the embed
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        print("Notification successfully sent to Discord.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification to Discord: {e}")

if __name__ == "__main__":
    # Example usage: Fetch latest event from DB and simulate sending notification
    latest_event = get_latest_event_from_db()
    if latest_event:
        send_notification(latest_event)
    else:
        print("No events found in the database to send notification.") 