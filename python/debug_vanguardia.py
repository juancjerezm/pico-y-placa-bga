"""Check Vanguardia for Pico y Placa verification."""
import httpx, re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}

# Search Vanguardia for recent pico y placa articles
urls = [
    "https://www.vanguardia.com/bucaramanga/buscar/pico%20y%20placa/",
    "https://www.vanguardia.com/buscar/pico%20y%20placa/",
]

for url in urls:
    print(f"\n=== {url} ===")
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        print(f"Status: {r.status_code}, Length: {len(r.text)}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n", strip=True)
        
        # Search for digit pairs
        pairs = re.findall(r"(\d)\s*y\s*(\d)", text)
        weekday_pairs = re.findall(r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[^.]*?(\d)\s*y\s*(\d)", text, re.IGNORECASE)
        dates_2026 = re.findall(r"(\d{1,2}\s+de\s+\w+\s+(?:de\s+)?2026)", text)
        
        print(f"Digit pairs: {len(pairs)}")
        if pairs:
            for d in pairs[:8]:
                print(f"  {d[0]} y {d[1]}")
        print(f"Weekday matches: {len(weekday_pairs)}")
        for w in weekday_pairs:
            print(f"  {w[0]}: {w[1]} y {w[2]}")
        print(f"2026 dates: {dates_2026[:3]}")
        
        # Find article links
        links = soup.find_all("a", href=True)
        pico_links = [l for l in links if "pico" in (l.get_text() + l.get("href", "")).lower()]
        print(f"Pico-related links: {len(pico_links)}")
        for l in pico_links[:5]:
            print(f"  {l.get_text(strip=True)[:80]}")
            print(f"  href: {l['href'][:100]}")
        
        if r.status_code == 200 and len(text) > 1000:
            break  # Found working URL
    except Exception as e:
        print(f"Error: {e}")
