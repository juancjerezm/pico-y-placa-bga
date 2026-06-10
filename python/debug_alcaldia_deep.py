"""Deep-dive into the latest Alcaldia article for rotation digits."""
import httpx, re
from bs4 import BeautifulSoup

url = "https://www.bucaramanga.gov.co/noticias/nuevas-disposiciones-del-pico-y-placa-en-bucaramanga-rigen-desde-el-martes-1-de-julio/"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

soup = BeautifulSoup(r.text, "html.parser")

# Find the article body
article = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body|single|nota", re.I)) or soup
text = article.get_text("\n", strip=True)

# Look for PDF links (resolutions often linked as PDFs)
pdfs = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
print(f"PDF links: {len(pdfs)}")
for p in pdfs[:5]:
    print(f"  {p.get('href','')[:120]}")
    print(f"  text: {p.get_text(strip=True)[:80]}")

# Look for links to DTB or resolutions
links = soup.find_all("a", href=True)
for l in links:
    href = l.get("href", "")
    text = l.get_text(strip=True).lower()
    if any(w in href.lower() or w in text for w in ["resolucion", "resolución", "dtb", "transito", "tránsito", "854", "descargar"]):
        print(f"\nLink: {href[:150]}")
        print(f"Text: {l.get_text(strip=True)[:100]}")

# Also check for images/infographics (sometimes the rotation is posted as an image)
imgs = soup.find_all("img")
for img in imgs:
    src = img.get("src", "")
    alt = img.get("alt", "")
    if "pico" in (src + alt).lower() or "placa" in (src + alt).lower() or "rotacion" in (src + alt).lower() or "rotación" in (src + alt).lower():
        print(f"\nImage: src={src[:150]}")
        print(f"Alt: {alt[:100]}")

# Search for the actual resolution number mentioned
print("\n=== Key resolution info ===")
for pattern in [r"Resolución\s+\d+", r"resolución\s+\d+", r"854", r"017", r"028", r"790", r"626"]:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"  {pattern}: {matches}")
