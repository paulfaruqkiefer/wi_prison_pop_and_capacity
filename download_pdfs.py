import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Base URL and target page
BASE_URL = "https://doc.wi.gov"
PAGE_URL = "https://doc.wi.gov/Pages/DataResearch/DataAndReports.aspx"

# Setup local storage
os.makedirs("doc_reports/weekly", exist_ok=True)
os.makedirs("doc_reports/archives", exist_ok=True)

def scrape_doc_data():
    response = requests.get(PAGE_URL)
    if response.status_code != 200:
        print(f"Failed to load page: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # 1. Scrape Current Weekly PDF links
    # These are usually inside a <div> that contains "WeeklyPopulationReports" in the href
    print("Searching for current weekly reports...")
    for link in soup.find_all('a', href=True):
        href = link['href']
        if "WeeklyPopulationReports" in href and href.endswith(".pdf"):
            full_url = urljoin(BASE_URL, href)
            file_name = os.path.join("doc_reports/weekly", href.split('/')[-1])
            download_file(full_url, file_name)

    # 2. Scrape Archived ZIP links
    # These are within the div with id "divArchivedWPR" as you noted
    print("\nSearching for archived ZIP files...")
    archive_div = soup.find('div', id='divArchivedWPR')
    if archive_div:
        for link in archive_div.find_all('a', href=True):
            href = link['href']
            if href.endswith(".zip"):
                full_url = urljoin(BASE_URL, href)
                file_name = os.path.join("doc_reports/archives", href.split('/')[-1])
                download_file(full_url, file_name)
    else:
        print("Archived div not found. Checking general links for archived zips...")

def download_file(url, local_path):
    if os.path.exists(local_path):
        print(f"Skipping (already exists): {local_path}")
        return
    
    try:
        print(f"Downloading: {url}")
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"Error downloading {url}: {e}")

if __name__ == "__main__":
    scrape_doc_data()