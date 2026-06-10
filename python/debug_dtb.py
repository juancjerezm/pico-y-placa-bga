"""Debug: analyze DTB pico y placa page."""
import httpx, re
from bs4 import BeautifulSoup

url = "https://transitobucaramanga.gov.co/dtb/atencion-y-servicios-a-la-ciudadania/pico-y-placa"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

print(f"Status: {r.status_code}, Length: {len(r.text)}")

soup = BeautifulSoup(r.text, "html.parser")
text = soup.get_text("\n", strip=True)

# Digit pairs
digit_pairs = re.findall(r"(\d)\s*y\s*(\d)", text)
print(f"Digit pairs: {len(digit_pairs)}")
for d in digit_pairs[:10]:
    print(f"  {d[0]} y {d[1]}")

# Weekday-digit matches
weekday_matches = re.findall(
    r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[^.]*?(\d)\s*y\s*(\d)",
    text, re.IGNORECASE
)
print(f"\nWeekday-digit matches: {len(weekday_matches)}")
for w in weekday_matches:
    print(f"  {w[0]}: {w[1]} y {w[2]}")

# Date ranges
dates = re.findall(r"(\d{1,2}\s+de\s+\w+\s+(?:al|hasta)\s+\d{1,2}\s+de\s+\w+\s+(?:de\s+)?\d{4})", text, re.IGNORECASE)
dates_iso = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
print(f"\nSpanish date ranges: {len(dates)}")
for d in dates[:3]:
    print(f"  {d}")
print(f"ISO dates: {len(dates_iso)}")

# Tables
tables = soup.find_all("table")
print(f"\nTables: {len(tables)}")
for i, t in enumerate(tables[:2]):
    rows = t.find_all("tr")
    print(f"  Table {i}: {len(rows)} rows")
    if rows:
        cells = rows[0].find_all(["td", "th"])
        print(f"  Headers: {[c.get_text(strip=True)[:30] for c in cells[:6]]}")

# Key content area
for tag in ["article", "main", "div"]:
    area = soup.find(tag, class_=re.compile("content|entry|post|page", re.I))
    if area:
        area_text = area.get_text("\n", strip=True)
        print(f"\nMain content area <{tag}>: {len(area_text)} chars")
        for line in area_text.split("\n")[:30]:
            line = line.strip()
            if len(line) > 10:
                print(f"  {line[:120]}")
        break
