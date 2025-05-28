import requests
from bs4 import BeautifulSoup
import time
import re
import json
import os
from datetime import datetime # Import datetime to add timestamps
import sqlite3 # Import sqlite3
import notification_service # Import notification_service

# 美國勞工統計局 (BLS) 非農就業數據新聞稿 URL
BLS_NONFARM_URL = "https://www.bls.gov/news.release/empsit.nr0.htm"

BLS_API_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
API_KEY_FILE = 'api_key.txt'

DATABASE_FILE = 'economic_events.db'

def is_event_in_database(series_id, year, period, value):
    """Checks if an event with the given series_id, year, period, and value already exists in the database."""
    conn = None
    exists = False
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        print(f"Checking database for event: series_id={series_id}, year={year}, period={period}, value={value}")

        cursor.execute("""
            SELECT 1 FROM events
            WHERE series_id = ? AND year = ? AND period = ? AND value = ?
            LIMIT 1;
        """, (series_id, year, period, value))

        row = cursor.fetchone()
        if row:
            exists = True
            print(f"Event found in database: series_id={series_id}, year={year}, period={period}, value={value}")
        else:
            print(f"Event NOT found in database: series_id={series_id}, year={year}, period={period}, value={value}")

    except sqlite3.Error as e:
        print(f"Database error while checking for event existence: {e}")
    finally:
        if conn:
            conn.close()

    return exists

def extract_nonfarm_data_from_html(html_content):
    """從 BLS 非農就業數據新聞稿的 HTML 內容中提取數據"""
    print("正在從提供的 HTML 內容中提取數據...")
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # 查找包含新聞稿文本的 <pre> 標籤
        pre_tag = soup.find('pre')

        if pre_tag:
            news_text = pre_tag.get_text()

            # 使用更穩健的正則表達式提取關鍵數據和日期
            payroll_match = re.search(r"Total nonfarm payroll employment (?:increased|decreased) by (\d+,?\d*)", news_text)
            unemployment_match = re.search(r"the unemployment rate was\s*(?:unchanged at|was|rose to|declined to)\s*(\d+\.?\d*)\s*percent", news_text)
            date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", news_text)

            data = {}
            if payroll_match:
                data['nonfarm_payroll_change'] = payroll_match.group(1)
            if unemployment_match:
                data['unemployment_rate'] = unemployment_match.group(1)
            if date_match:
                data['release_date'] = date_match.group(0)

            if data:
                print(f"成功提取到數據: {data}")
                return data
            else:
                print("未在提供的 HTML 內容中找到非農就業數據或日期。請檢查提取邏輯或內容。")
                return None

        else:
            print("未在提供的 HTML 內容中找到包含新聞稿文本的 <pre> 標籤。")
            return None

    except Exception as e:
        print(f"處理 HTML 內容時發生錯誤: {e}")
        return None

def fetch_nonfarm_data_via_requests():
    """通過 requests 從 BLS 網站抓取非農就業數據 (可能被阻擋)"""
    print(f"正在嘗試通過 requests 從 {BLS_NONFARM_URL} 抓取數據...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.bls.gov/'
    }
    try:
        response = requests.get(BLS_NONFARM_URL, headers=headers)
        response.raise_for_status()
        # 如果成功獲取，則調用新的提取函數
        return extract_nonfarm_data_from_html(response.text)

    except requests.exceptions.RequestException as e:
        print(f"通過 requests 抓取數據時發生錯誤: {e}")
        return None
    except Exception as e:
        print(f"處理數據時發生錯誤: {e}")
        return None

def get_bls_api_key():
    """Reads the BLS API key from api_key.txt."""
    if not os.path.exists(API_KEY_FILE):
        print(f"Error: API key file '{API_KEY_FILE}' not found.")
        print("Please create a file named api_key.txt in the project root and paste your API key inside.")
        return None
    with open(API_KEY_FILE, 'r') as f:
        return f.read().strip()

def fetch_bls_data(api_key, series_ids, start_year, end_year):
    """Fetches data from the BLS Public Data API."""
    headers = {'Content-type': 'application/json'}
    # Construct the request payload
    data = json.dumps({
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
        "registrationkey": api_key
    })

    try:
        response = requests.post(BLS_API_BASE_URL, headers=headers, data=data)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from BLS API: {e}")
        return None

def extract_economic_data(data):
    """Extracts and formats economic data from the BLS API response."""
    extracted_data = {}
    if data and data['status'] == 'REQUEST_SUCCEEDED':
        for series in data['Results']['series']:
            series_id = series['seriesID']
            # Ensure we have at least two data points to get current and previous
            if len(series['data']) >= 2:
                latest_data = series['data'][0] # Latest data point
                previous_data = series['data'][1] # Previous data point

                extracted_data[series_id] = {
                    'latest': {
                        'year': latest_data['year'],
                        'period': latest_data['period'],
                        'value': latest_data['value'],
                        'footnotes': latest_data.get('footnotes', []),
                    },
                    'previous': {
                        'year': previous_data['year'],
                        'period': previous_data['period'],
                        'value': previous_data['value'],
                        'footnotes': previous_data.get('footnotes', []),
                    }
                }
            elif len(series['data']) == 1:
                 # If only one data point, we only have the latest
                 latest_data = series['data'][0]
                 extracted_data[series_id] = {
                    'latest': {
                        'year': latest_data['year'],
                        'period': latest_data['period'],
                        'value': latest_data['value'],
                        'footnotes': latest_data.get('footnotes', []),
                    },
                    'previous': None # No previous data available
                }
            else:
                 print(f"Warning: Not enough data points ({len(series['data'])}) for series {series_id} to get latest and previous.")
                 extracted_data[series_id] = None # No data available

    return extracted_data

def process_economic_data(extracted_data):
    """Processes extracted economic data and creates data release events."""
    print("\n--- Processing Economic Data and Creating Data Release Events ---")
    processed_events = []

    current_time = datetime.now().isoformat()

    # Create Data Release Events for each successfully extracted data point
    for series_id, data_points_dict in extracted_data.items():
        if data_points_dict and data_points_dict.get('latest'):
            latest_data = data_points_dict['latest']
            previous_data = data_points_dict.get('previous')

            year = latest_data['year']
            period = latest_data['period']
            value = latest_data['value']
            previous_value = previous_data['value'] if previous_data else 'N/A'

            # --- 模擬預期值 (Simulated Expected Value) - 固定值用於模型測試 ---
            # IMPORTANT: 在實際系統中，這部分需要從金融數據提供商獲取真實的預期值。
            #            目前的實現是固定值，僅用於模型測試和功能展示。
            simulated_expected_value = "N/A" # 預設值，如果沒有特定模擬值則顯示 N/A
            # 根據 series_id 設定模擬的固定預期值
            if series_id == 'LNS14000000':
                 simulated_expected_value = "~3.9%" # 模擬失業率預期值
            elif series_id == 'CES0000000001':
                 simulated_expected_value = "~180K" # 模擬非農就業人數預期值
            elif series_id == 'CUUR0000SA0':
                 simulated_expected_value = "~3.4%" # 模擬 CPI 預期值
            elif series_id == 'WPUID000000':
                 simulated_expected_value = "~2.0%" # 模擬 PPI 預期值
            # -----------------------------------------------------------

            # Check if this event already exists in the database
            if not is_event_in_database(series_id, year, period, value):

                series_name = "Unknown Series"
                # Map series_id to a human-readable name
                if series_id == 'LNS14000000':
                    series_name = "Unemployment Rate"
                elif series_id == 'CES0000000001':
                    series_name = "Nonfarm Payroll"
                elif series_id == 'CUUR0000SA0':
                    series_name = "CPI (All items)"
                elif series_id == 'WPUID000000':
                     series_name = "PPI (All commodities)"

                event_type = "Data Release"
                # Update event description to include previous and expected values
                event_description = f"{series_name} data released: Latest = {value}, Previous = {previous_value}, Expected = {simulated_expected_value}, Period = {year} {period}"

                event = {
                    "type": event_type,
                    "description": event_description,
                    "value": value,
                    "previous_value": previous_value, # Add previous value
                    "expected_value": simulated_expected_value, # Add simulated expected value
                    "year": year,
                    "period": period,
                    "timestamp": current_time,
                    "source": "BLS API",
                    "series_id": series_id
                }
                processed_events.append(event)
                print(f"Created NEW Event: {event_description}") # Indicate it's a new event
            else:
                print(f"Event for {series_id} ({year} {period}, Value: {value}) already exists in database. Skipping notification and save.")

    # TODO: Refine event structure and add more context if needed (e.g., link to BLS release page)

    return processed_events # Return list of data release events

def init_database():
    """Initializes the SQLite database and creates the events table."""
    print(f"\nInitializing database: {DATABASE_FILE}")
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Create events table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                description TEXT,
                value TEXT,
                year TEXT,
                period TEXT,
                timestamp TEXT,
                source TEXT,
                series_id TEXT,
                previous_value TEXT,
                expected_value TEXT
            );
        """)

        conn.commit()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def save_events_to_database(events):
    """Saves a list of events to the database."""
    if not events:
        print("No events to save to database.")
        return

    print(f"\nSaving {len(events)} events to database: {DATABASE_FILE}")
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Prepare data for insertion
        data_to_insert = [
            (event.get('type'), event.get('description'), event.get('value'),
             event.get('year'), event.get('period'), event.get('timestamp'),
             event.get('source'), event.get('series_id'),
             event.get('previous_value'), event.get('expected_value')) # Include new fields
            for event in events
        ]

        # Insert data into the events table
        cursor.executemany("""
            INSERT INTO events (type, description, value, year, period, timestamp, source, series_id, previous_value, expected_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, data_to_insert)

        conn.commit()
        print("Events saved to database successfully.")

    except sqlite3.Error as e:
        print(f"Database error while saving events: {e}")
    finally:
        if conn:
            conn.close()

# 模擬定時抓取
if __name__ == "__main__":
    # Initialize the database on script start
    init_database()

    api_key = get_bls_api_key()
    if not api_key:
        print("BLS API key not available. Exiting.")
        exit()

    # Define the series IDs for Unemployment Rate, Nonfarm Payroll, CPI, and PPI
    series_ids = [
        'LNS14000000',  # Unemployment Rate
        'CES0000000001',  # Nonfarm Payroll: Total Nonfarm
        'CUUR0000SA0',  # CPI: All items, U.S. city average, unadjusted
        'WPUID000000'  # PPI: All commodities, unadjusted
    ]

    # Monitoring loop
    while True:
        print(f"\n--- Checking for new data at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

        # Fetch data for the current year. We assume BLS API returns latest data first.
        current_year = datetime.now().year
        # To get previous year's data for comparison, fetch data for current and previous year
        bls_data = fetch_bls_data(api_key, series_ids, current_year - 1, current_year)

        if bls_data:
            extracted_data = extract_economic_data(bls_data)
            if extracted_data:
                # Process the extracted data and identify NEW events
                # process_economic_data function now only creates events for new data
                processed_events = process_economic_data(extracted_data)

                # Use the identified NEW events for storage and notification
                if processed_events:
                    print(f"\nDetected {len(processed_events)} new event(s).")
                    # Save new events to database
                    save_events_to_database(processed_events)

                    # Send notifications for new events
                    print("\n--- Triggering Notifications for NEW Events ---")
                    for event in processed_events:
                        notification_service.send_notification(event)

                else:
                    print("No new events detected.")

            else:
                print("No data extracted successfully from API response.")
        else:
            print("Failed to fetch data from BLS API.")

        # Wait for 5 minutes before next check...
        print("\nWaiting for 1 minutes before next check...")
        time.sleep(60) # Wait for 60 seconds (1 minute)

    # Keep the placeholder for future HTML parsing if needed, but comment it out for now
    # html_content = """
    # ... paste the full HTML content from the BLS news release page here ...
    # """
    # nonfarm_data = extract_nonfarm_data_from_html(html_content)
    # print(f"Extracted Nonfarm Data (from HTML): {nonfarm_data}")

    # TODO: 未來集成 Firecrawl 的調用結果，將其傳遞給 extract_nonfarm_data_from_html 函數進行處理
    # 示例：
    # firecrawl_html_content = "...從 Firecrawl 獲取的 HTML 內容..."
    # nonfarm_data_firecrawl = extract_nonfarm_data_from_html(firecrawl_html_content)
    # if nonfarm_data_firecrawl:
    #     print("Firecrawl 提取測試成功：", nonfarm_data_firecrawl)
    # else:
    #     print("Firecrawl 提取測試失敗。")

    # TODO: 將抓取到的數據存儲到數據庫或發送通知
    # TODO: 實現定時抓取或事件觸發邏輯

    # 模擬等待 5 分鐘 (在實際的定時任務中需要)
    # time.sleep(300) # 5 minutes 