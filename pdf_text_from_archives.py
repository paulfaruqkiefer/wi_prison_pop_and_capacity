import os
import re
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
import pdfplumber

# --- CONFIGURATION ---
BASE_DIR = "doc_reports/extracted_pdfs"
OUTPUT_CSV = "wi_prison_stats_final_attempt.csv"

def clean_number(text):
    if not text: return None
    cleaned = re.sub(r'[^\d]', '', text)
    try:
        val = int(cleaned)
        # Strict range for WI: Capacity/Pop is always between 10k and 28k
        if 10000 < val < 28000: return val
    except: return None
    return None

def extract_legacy_ocr(pdf_path):
    try:
        # 500 DPI is non-negotiable for the 2001-2009 reports
        images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=500)
        img = images[0].convert('L')
        width, height = img.size
        
        # 1. DEFINE THE DATA ZONE
        # We target the upper-middle section of the page (where the summary table lives)
        # Relative coordinates: (left, top, right, bottom)
        # This zone is designed to catch 'Adult Institutions' but skip headers/footers
        zone = img.crop((int(width * 0.1), int(height * 0.12), int(width * 0.9), int(height * 0.45)))
        
        # 2. Get Data with Coordinates from the Zone
        data = pytesseract.image_to_data(zone, config=r'--oem 3 --psm 6', output_type=pytesseract.Output.DICT)
        
        rows = {}
        for i in range(len(data['text'])):
            val = clean_number(data['text'][i])
            if val:
                y = data['top'][i]
                # Group numbers by their Y-coordinate (within 30px)
                # We round to the nearest 30 to "snap" numbers onto the same line
                row_key = (y // 30) * 30
                if row_key not in rows: rows[row_key] = []
                rows[row_key].append((data['left'][i], val))

        # 3. Analyze the Rows
        sorted_y = sorted(rows.keys())
        for y in sorted_y:
            row_vals = sorted(rows[y], key=lambda x: x[0])
            nums = [v[1] for v in row_vals]
            
            # The Summary row always has at least 2 numbers in the 12k-25k range.
            # Usually it's Capacity, then Total Pop.
            if len(nums) >= 2:
                # To avoid the "Subtotal" row error, we check if the row 
                # looks like our target. The FIRST row that fits this criteria
                # in our zone is the "ADULT INSTITUTIONS" total.
                return nums[0], nums[1]
                
    except Exception as e:
        print(f"Error: {e}")
    return None, None

def main():
    results = []
    for year_folder in sorted(os.listdir(BASE_DIR)):
        folder_path = os.path.join(BASE_DIR, year_folder)
        if not os.path.isdir(folder_path): continue
        
        for file_name in sorted(os.listdir(folder_path)):
            if not file_name.endswith(".pdf"): continue
            path = os.path.join(folder_path, file_name)
            
            # Using OCR for all pre-2016 files
            cap, pop = extract_legacy_ocr(path)
                
            print(f"[{year_folder}] {file_name} -> Cap: {cap}, Pop: {pop}")
            results.append({"date": file_name, "capacity": cap, "population": pop})

    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False)

if __name__ == "__main__":
    main()