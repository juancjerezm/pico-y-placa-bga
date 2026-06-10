"""Fetch Alcaldia article and dump the relevant HTML section."""
import httpx, re
from bs4 import BeautifulSoup

url = "https://www.bucaramanga.gov.co/noticias/nuevas-disposiciones-del-pico-y-placa-en-bucaramanga-rigen-desde-el-martes-1-de-julio/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9",
}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

soup = BeautifulSoup(r.text, "html.parser")

# Find the article content area
article = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body|single|nota|contenido", re.I)) or soup

# Get all text
text = article.get_text("\n", strip=True)

# Search for digit patterns specifically around weekday names
lines = text.split("\n")
for i, line in enumerate(lines):
    line_lower = line.lower().strip()
    if any(w in line_lower for w in ["lunes", "martes", "miércoles", "miercoles", "jueves", "viernes", "dígito", "digito", "placa"]):
        # Show context (2 lines before and after)
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            marker = ">>>" if j == i else "   "
            print(f"{marker} {lines[j].strip()[:150]}")
        print()

# Also look for images that might contain the rotation table
imgs = soup.find_all("img")
for img in imgs:
    src = img.get("src", "")
    if any(w in src.lower() for w in ["pico", "placa", "rotacion", "rotación", "restriccion"]):
        print(f"IMAGE: {src}")

# Check for iframes or embedded content
iframes = soup.find_all("iframe")
print(f"\nIframes: {len(iframes)}")
for f in iframes:
    print(f"  {f.get('src', '')[:150]}")

# Check for any div/article with inline styles or data attributes that might hide content
for tag in soup.find_all(["div", "section", "figure"]):
    style = tag.get("style", "")
    cls = " ".join(tag.get("class", []))
    if "display:none" in style or "hidden" in cls:
        text = tag.get_text(strip=True)
        if "pico" in text.lower():
            print(f"\nHIDDEN content: {text[:200]}")
