"""Try DTB page with proper headers."""
import httpx, re

url = "https://transitobucaramanga.gov.co/dtb/atencion-y-servicios-a-la-ciudadania/pico-y-placa"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

if r.status_code != 200:
    print(f"Response: {r.text[:500]}")
    print(f"\nHeaders: {dict(r.headers)}")
else:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    
    # Digit pairs
    digit_pairs = re.findall(r"(\d)\s*y\s*(\d)", text)
    print(f"Digit pairs: {len(digit_pairs)}")
    for d in digit_pairs[:10]:
        print(f"  {d[0]} y {d[1]}")
    
    # Weekday matches
    wd_matches = re.findall(r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[^.]*?(\d)\s*y\s*(\d)", text, re.IGNORECASE)
    print(f"Weekday matches: {len(wd_matches)}")
    for w in wd_matches:
        print(f"  {w[0]}: {w[1]} y {w[2]}")
    
    # Check for tables
    tables = soup.find_all("table")
    print(f"Tables: {len(tables)}")
