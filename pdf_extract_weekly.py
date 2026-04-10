import os
import re
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
import csv

# --- CONFIGURATION ---
WEEKLY_DIR = "doc_reports/weekly" # Adjusted to your weekly folder
OUTPUT_CSV = "wi_prison_stats_weekly.csv"

def clean_number(text):
    if not text: return None
    cleaned = re.sub(r'[^\d]', '', text)
    try:
        val = int(cleaned)
        # Wisconsin range check
        if 10000 < val < 30000: return val
    except: return None
    return None

def parse_filename_date(filename):
    """Converts fri_01_02_2026.pdf to 2026-01-02 for better sorting."""
    match = re.search(r'(\d{2})_(\d{2})_(\d{4})', filename)
    if match:
        mm, dd, yyyy = match.groups()
        return f"{yyyy}-{mm}-{dd}"
    return filename.replace(".pdf", "")

def extract_zonal_ocr(pdf_path):
    try:
        # 500 DPI for high precision
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=500)
        img = images[0].convert('L')
        width, height = img.size
        
        # This zone targets the 'Adult Institutions' summary row
        zone = img.crop((int(width * 0.1), int(height * 0.12), int(width * 0.9), int(height * 0.45)))
        data = pytesseract.image_to_data(zone, config=r'--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        
        rows = {}
        for i in range(len(data['text'])):
            val = clean_number(data['text'][i])
            if val:
                y = data['top'][i]
                # Snaps misaligned numbers into 30px 'rows'
                row_key = (y // 30) * 30
                if row_key not in rows: rows[row_key] = []
                rows[row_key].append((data['left'][i], val))

        sorted_y = sorted(rows.keys())
        for y in sorted_y:
            row_vals = sorted(rows[y], key=lambda x: x[0])
            nums = [v[1] for v in row_vals]
            if len(nums) >= 2:
                # Returns [Capacity, Population]
                return nums[0], nums[1]
    except Exception as e:
        print(f"Error on {pdf_path}: {e}")
    return None, None

def main():
    headers = ["file_date", "formatted_date", "capacity", "population"]
    
    # Check if folder exists
    if not os.path.exists(WEEKLY_DIR):
        print(f"Error: Folder '{WEEKLY_DIR}' not found. Please check the path.")
        return

    # Write headers
    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

    # Get file list and process
    files = [f for f in sorted(os.listdir(WEEKLY_DIR)) if f.endswith(".pdf")]
    
    print(f"Found {len(files)} weekly reports. Starting extraction...")

    for file_name in files:
        path = os.path.join(WEEKLY_DIR, file_name)
        
        formatted_date = parse_filename_date(file_name)
        cap, pop = extract_zonal_ocr(path)
        
        print(f"Processed: {formatted_date} -> Cap: {cap}, Pop: {pop}")

        # Safe-save to CSV
        with open(OUTPUT_CSV, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow({
                "file_date": file_name,
                "formatted_date": formatted_date,
                "capacity": cap,
                "population": pop
            })

    print(f"\nDone! Weekly data saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()