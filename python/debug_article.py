"""Debug: fetch and analyze full article content for rotation data."""
import httpx, re

url = "https://www.bucaramanga.gov.co/noticias/nueva-rotacion-de-pico-y-placa-en-bucaramanga-inicia-hoy/"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

# Find all text content
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")

# Look for the article body
body = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body", re.I)) or soup
text = body.get_text("\n", strip=True)

# Find digit pairs
digit_pairs = re.findall(r"(\d)\s*y\s*(\d)", text)
print(f"Total digit pairs: {len(digit_pairs)}")
for d in digit_pairs[:10]:
    print(f"  {d[0]} y {d[1]}")

# Find weekdays with digits
weekday_pattern = re.findall(r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[^.]*?(\d)\s*y\s*(\d)", text, re.IGNORECASE)
print(f"\nWeekday-digit matches: {len(weekday_pattern)}")
for w in weekday_pattern:
    print(f"  {w[0]}: {w[1]} y {w[2]}")

# Find date ranges
dates = re.findall(r"(\d{1,2}\s+de\s+\w+\s+(?:al|hasta)\s+\d{1,2}\s+de\s+\w+\s+(?:de\s+)?\d{4})", text, re.IGNORECASE)
dates += re.findall(r"(\d{4}-\d{2}-\d{2}.*?\d{4}-\d{2}-\d{2})", text)
print(f"\nDate ranges: {len(dates)}")
for d in dates[:3]:
    print(f"  {d[:120]}")

# Check for table elements
tables = soup.find_all("table")
print(f"\nTables found: {len(tables)}")

# Print relevant text snippet around rotation
for snippet in re.finditer(r".{0,100}pico.{0,100}", text, re.IGNORECASE):
    print(f"\nSnippet: ...{snippet.group()[:200]}...")
    if snippet.start() > 5000:
        break
