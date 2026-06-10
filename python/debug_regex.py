"""Debug: test regex on article text directly."""
import httpx, re
from bs4 import BeautifulSoup
from scraper.scraper import _RE_WEEKDAY_DIGITS

url = "https://www.bucaramanga.gov.co/noticias/nueva-rotacion-de-pico-y-placa-en-bucaramanga-inicia-hoy/"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

soup = BeautifulSoup(r.text, "html.parser")
article = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body", re.I)) or soup
text = article.get_text("\n", strip=True)

# Test the regex
matches = list(_RE_WEEKDAY_DIGITS.finditer(text))
print(f"Regex matches: {len(matches)}")
for m in matches:
    print(f"  Groups: {[(i, g) for i, g in enumerate(m.groups()) if g is not None]}")

# Test line by line
from scraper.scraper import _extract_digits_line_by_line
result = _extract_digits_line_by_line(text.lower())
print(f"\nLine-by-line: {result}")

# Check actual text around weekdays
for wd in ["lunes", "martes", "miércoles", "jueves", "viernes"]:
    idx = text.lower().find(wd)
    if idx >= 0:
        snippet = text[max(0,idx-5):idx+50]
        print(f"  '{wd}' → ...{snippet}...")
