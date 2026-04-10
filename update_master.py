import os
import re
import csv
import requests
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import shutil

# --- CONFIGURATION ---
BASE_URL = "https://doc.wi.gov"
PAGE_URL = "https://doc.wi.gov/Pages/DataResearch/DataAndReports.aspx"
MASTER_CSV = "wi_prison_stats_master.csv"
BACKUP_DIR = "backups"
TEMP_PDF_DIR = "temp_weekly_pdfs"

def clean_number(text):
    if not text: return None
    cleaned = re.sub(r'[^\d]', '', text)
    try:
        val = int(cleaned)
        # Range check for Wisconsin Adult Institutions
        if 10000 < val < 35000: return val
    except: return None
    return None

def parse_filename_date(filename):
    """Converts fri_01_02_2026.pdf to 2026-01-02."""
    match = re.search(r'(\d{2})_(\d{2})_(\d{4})', filename)
    if match:
        mm, dd, yyyy = match.groups()
        return f"{yyyy}-{mm}-{dd}"
    return None

def extract_zonal_ocr(pdf_path):
    """The verified Zonal OCR logic for summary rows."""
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=500)
        img = images[0].convert('L')
        width, height = img.size
        
        # Zone targeting 'Adult Institutions' summary row
        zone = img.crop((int(width * 0.1), int(height * 0.12), int(width * 0.9), int(height * 0.45)))
        data = pytesseract.image_to_data(zone, config=r'--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        
        rows = {}
        for i in range(len(data['text'])):
            val = clean_number(data['text'][i])
            if val:
                y = data['top'][i]
                row_key = (y // 30) * 30
                if row_key not in rows: rows[row_key] = []
                rows[row_key].append((data['left'][i], val))

        sorted_y = sorted(rows.keys())
        for y in sorted_y:
            row_vals = sorted(rows[y], key=lambda x: x[0])
            nums = [v[1] for v in row_vals]
            if len(nums) >= 2:
                return nums[0], nums[1]
    except Exception as e:
        print(f"OCR Error on {pdf_path}: {e}")
    return None, None

def main():
    # 1. Load Master and Backup
    if not os.path.exists(MASTER_CSV):
        print(f"Error: {MASTER_CSV} not found. Ensure it is in the repo root.")
        return

    df_master = pd.read_csv(MASTER_CSV)
    # Ensure date column is datetime for comparison
    df_master['formatted_date_dt'] = pd.to_datetime(df_master['formatted_date'])
    last_date = df_master['formatted_date_dt'].max()
    print(f"Last date in master: {last_date.date()}")

    if not os.path.exists(BACKUP_DIR): 
        os.makedirs(BACKUP_DIR)
    
    backup_path = f"{BACKUP_DIR}/master_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    shutil.copy(MASTER_CSV, backup_path)
    print(f"Backup created: {backup_path}")

    # 2. Scrape for new PDFs
    print(f"Scraping {PAGE_URL}...")
    response = requests.get(PAGE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)

    new_rows = []
    
    # Check all links for weekly reports
    for link in soup.find_all('a', href=True):
        href = link['href']
        if "WeeklyPopulationReports" in href and href.endswith(".pdf"):
            filename = href.split('/')[-1]
            file_date_str = parse_filename_date(filename)
            
            if file_date_str:
                file_date_dt = pd.to_datetime(file_date_str)
                
                # 3. Only process if the file date is newer than our max date
                if file_date_dt > last_date:
                    print(f"Found new report: {filename}")
                    full_url = urljoin(BASE_URL, href)
                    local_path = os.path.join(TEMP_PDF_DIR, filename)
                    
                    # Download
                    pdf_res = requests.get(full_url)
                    with open(local_path, 'wb') as f:
                        f.write(pdf_res.content)
                    
                    # OCR
                    cap, pop = extract_zonal_ocr(local_path)
                    if cap and pop:
                        new_rows.append({
                            "formatted_date": file_date_str,
                            "file_date": filename,
                            "capacity": cap,
                            "population": pop
                        })
                        print(f"Success: {file_date_str} -> {cap} / {pop}")
                    else:
                        print(f"Failed to extract numbers from {filename}")

    # 4. Update Master CSV
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Drop temporary helper column before concat
        df_master = df_master.drop(columns=['formatted_date_dt'])
        
        df_final = pd.concat([df_master, df_new], ignore_index=True)
        # Sort by date
        df_final['formatted_date'] = pd.to_datetime(df_final['formatted_date'])
        df_final = df_final.sort_values(by='formatted_date')
        
        # Save back to root
        df_final.to_csv(MASTER_CSV, index=False)
        print(f"Master CSV updated with {len(new_rows)} new entries.")
    else:
        print("No new data found.")

    # Cleanup
    if os.path.exists(TEMP_PDF_DIR):
        shutil.rmtree(TEMP_PDF_DIR)

if __name__ == "__main__":
    main()