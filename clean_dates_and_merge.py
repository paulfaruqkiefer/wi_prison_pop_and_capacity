import pandas as pd
import re
from datetime import datetime

# --- CONFIGURATION ---
LEGACY_CSV = "wi_prison_stats_final_attempt.csv"
WEEKLY_CSV = "wi_prison_stats_weekly.csv"
FINAL_MASTER_CSV = "wi_prison_stats_master.csv"

def parse_messy_date(text):
    """
    Attempts to extract and standardize dates from chaotic filenames.
    Target format: YYYY-MM-DD
    """
    if not text or not isinstance(text, str):
        return None

    # Pattern 1: YYYY.MM.DD or YYYY-MM-DD (e.g., 1999.01.01)
    match1 = re.search(r'(\d{4})[./-](\d{2})[./-](\d{2})', text)
    if match1:
        yyyy, mm, dd = match1.groups()
        return f"{yyyy}-{mm}-{dd}"

    # Pattern 2: MMDDYYYY (e.g., 04032020 or 03202020Corrected)
    match2 = re.search(r'(\d{2})(\d{2})(\d{4})', text)
    if match2:
        mm, dd, yyyy = match2.groups()
        return f"{yyyy}-{mm}-{dd}"
    
    return None

def main():
    # 1. Load Legacy Data
    print("Standardizing legacy dates...")
    df_legacy = pd.read_csv(LEGACY_CSV)
    
    # Store original name, then parse new date
    df_legacy['file_date'] = df_legacy['date'] # Keep original filename
    df_legacy['formatted_date'] = df_legacy['date'].apply(parse_messy_date)
    
    # Drop the old 'date' column and reorder to match weekly format
    df_legacy = df_legacy[['formatted_date', 'file_date', 'capacity', 'population']]

    # 2. Load Weekly Data
    print("Loading weekly data...")
    df_weekly = pd.read_csv(WEEKLY_CSV)
    
    # Reorder weekly to match the order we just set for legacy
    # weekly has: file_date, formatted_date, capacity, population
    df_weekly = df_weekly[['formatted_date', 'file_date', 'capacity', 'population']]

    # 3. Combine
    print("Merging dataframes...")
    master_df = pd.concat([df_legacy, df_weekly], ignore_index=True)

    # 4. Clean up
    # Remove rows where date couldn't be parsed (if any)
    initial_count = len(master_df)
    master_df = master_df.dropna(subset=['formatted_date'])
    
    # Convert to actual datetime objects for robust sorting
    master_df['sort_date'] = pd.to_datetime(master_df['formatted_date'], errors='coerce')
    master_df = master_df.sort_values(by='sort_date').drop(columns=['sort_date'])

    # 5. Final Save
    master_df.to_csv(FINAL_MASTER_CSV, index=False)
    
    dropped = initial_count - len(master_df)
    print(f"Success! Master file saved: {FINAL_MASTER_CSV}")
    print(f"Total rows: {len(master_df)} (Dropped {dropped} unparseable rows)")

if __name__ == "__main__":
    main()