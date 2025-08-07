import os
import re
import time
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import List, Optional

OUTPUT_DIR = r"D:\Project_Python\DLkomik2\DL"
CHAPTER_TOKEN = "-chapter-"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_rendered_html(url: str) -> str:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2)
    html = driver.page_source
    driver.quit()
    return html

def get_chapter_links(manga_url: str) -> List[str]:
    html = get_rendered_html(manga_url)
    soup = BeautifulSoup(html, 'lxml')
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        if not hasattr(a, "get"):
            continue
        href: str = str(a.get("href", "")).strip()
        if CHAPTER_TOKEN in href.lower():
            links.append(urljoin(manga_url, href.rstrip('/')))
    links = sorted(set(links), key=lambda u: extract_chapter_num(u))
    return links

def extract_chapter_num(url: str) -> float:
    m = re.search(r"chapter-([0-9]+(?:\.[0-9]+)?)", url)
    return float(m.group(1)) if m else 0

def download_chapter(ch_url: str):
    print(f"=== Chapter: {ch_url} ===")
    html = get_rendered_html(ch_url)
    soup = BeautifulSoup(html, 'lxml')
    reader = soup.find("div", id="readerarea")
    if not reader:
        print("  [!] Tidak menemukan area gambar.")
        return
    images = reader.find_all('img')
    print(f"  Ditemukan {len(images)} gambar.")

    chapter_num = extract_chapter_num(ch_url) or "unknown"
    slug = ch_url.split(CHAPTER_TOKEN)[0].split('/')[-1]
    save_dir = os.path.join(OUTPUT_DIR, slug, f"Ch{chapter_num}")
    os.makedirs(save_dir, exist_ok=True)

    for idx, img in enumerate(images):
        img_url: str = img.get('src') or img.get('data-src')
        if not img_url:
            continue
        img_url = urljoin(ch_url, img_url)
        img_name = os.path.join(save_dir, f"{idx+1:03d}.webp")
        print(f"  Download {img_url}")
        try:
            resp = requests.get(img_url, headers=HEADERS, stream=True)
            if resp.status_code == 200:
                with open(img_name, 'wb') as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
        except Exception as e:
            print(f"  [ERR] {e}")
    print(f"  -> Selesai: {save_dir}")

def download_manga(manga_url: str, selected: Optional[List[float]] = None):
    chapters = get_chapter_links(manga_url)
    print(f"Ditemukan {len(chapters)} chapter.")

    if selected:
        chapters = [c for c in chapters if extract_chapter_num(c) in selected]
        print(f"Mendownload {len(chapters)} chapter sesuai pilihan: {selected}")

    for ch in chapters:
        download_chapter(ch)

def list_manga_and_chapters(manga_url: str):
    html = get_rendered_html(manga_url)
    soup = BeautifulSoup(html, 'lxml')
    # Ambil judul manga
    title_tag = soup.find("h1")
    title = title_tag.text.strip() if title_tag else "Unknown Title"
    print(f"\nJudul: {title}")

    # Ambil daftar chapter
    chapters = get_chapter_links(manga_url)
    print(f"Total {len(chapters)} chapter ditemukan:")
    for ch_url in chapters:
        ch_num = extract_chapter_num(ch_url)
        print(f"  Chapter {ch_num}: {ch_url}")

def list_manga_titles(list_url: str):
    html = get_rendered_html(list_url)
    soup = BeautifulSoup(html, 'lxml')
    manga_links = soup.select("div.bsx > a")
    print(f"\nDitemukan {len(manga_links)} judul manga di halaman ini:")
    for idx, a in enumerate(manga_links, 1):
        title = a.get("title") or a.text.strip()
        url = a.get("href")
        print(f"{idx}. {title} - {url}")

if __name__ == "__main__":
    print("=== KomikTap Downloader ===")
    print("1. Download manga")
    print("2. List judul & chapter dari 1 manga")
    print("3. List judul manga dari halaman list")
    menu = input("Pilih menu [1/2/3]: ").strip()
    if menu == "3":
        list_url = input("Masukkan URL halaman list manga: ").strip()
        if not list_url:
            print("URL tidak boleh kosong!")
        else:
            list_manga_titles(list_url)
    else:
        manga_url = input("Masukkan URL manga utama: ").strip()
        if not manga_url:
            print("URL tidak boleh kosong!")
        elif menu == "2":
            list_manga_and_chapters(manga_url)
        else:
            pilihan = input("Masukkan nomor chapter dipisah koma (kosongkan untuk semua): ").strip()
            if pilihan:
                selected = [float(x) for x in pilihan.split(',') if x.strip().replace('.', '', 1).isdigit()]
            else:
                selected = None
            download_manga(manga_url, selected)
