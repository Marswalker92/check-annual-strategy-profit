import re
import datetime
import pytz

file_path = "/home/young-ai/code/polymarket_relate/check-annual-strategy-profit/data/reports/polymarket_portfolio_report.md"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the pattern "Generated at: YYYY-MM-DD HH:MM:SS UTC"
    pattern = r"(Generated at:\s*)(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+UTC"
    
    def replacer(match):
        prefix = match.group(1)
        time_str = match.group(2)
        
        # Parse UTC time
        utc_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        utc_time = pytz.utc.localize(utc_time)
        
        # Convert to Berlin time
        berlin_tz = pytz.timezone("Europe/Berlin")
        berlin_time = utc_time.astimezone(berlin_tz)
        
        return f"{prefix}{berlin_time.strftime('%Y-%m-%d %H:%M:%S')} CET/CEST (Berlin)"

    new_content = re.sub(pattern, replacer, content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

except Exception as e:
    print(f"Error updating time: {e}")
