"""Debug: check the most recent article for rotation + dates."""
import httpx, re
from bs4 import BeautifulSoup
from scraper.scraper import extract_rotation_digits, extract_date_range, _RE_SPANISH_DATE_RANGE, _MONTHS_ES

url = "https://www.bucaramanga.gov.co/noticias/nuevas-disposiciones-del-pico-y-placa-en-bucaramanga-rigen-desde-el-martes-1-de-julio/"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
print(f"Status: {r.status_code}")

soup = BeautifulSoup(r.text, "html.parser")
article = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body", re.I)) or soup
text = article.get_text("\n", strip=True)

digits = extract_rotation_digits(text)
print(f"Digits: {digits}")

dates = extract_date_range(text)
print(f"Date range: {dates}")

# Check for any date pattern
for pat_name, pattern in [
    ("ISO range", r"(\d{4}-\d{2}-\d{2}).*?(?:al|hasta).*?(\d{4}-\d{2}-\d{2})"),
    ("Desde ISO", r"desde.*?(\d{4}-\d{2}-\d{2})"),
    ("Desde Spanish", r"desde\s+el\s+(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})"),
    ("Rige Spanish", r"rige\s+(?:desde\s+)?(?:el\s+)?(\d{1,2})\s+de\s+(\w+)"),
    ("Del al", r"del\s+(\d{1,2})\s+de\s+(\w+)\s+(?:al|hasta)\s+(\d{1,2})\s+de\s+(\w+)"),
]:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f"{pat_name}: {matches}")

# Check for quarter info
q_patterns = re.findall(r"(trimestre|semestre|cuatrimestre)\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
print(f"Quarter info: {q_patterns}")

# Print relevant snippet
for snippet in re.finditer(r".{0,80}(?:rige|desde|inicia|empieza|calendario|rotación|rotacion|vigente).{0,80}", text, re.IGNORECASE):
    print(f"\n  ...{snippet.group()[:200]}...")
    if len(list(re.finditer(r".{0,80}(?:rige|desde|inicia|empieza)", text, re.IGNORECASE))) > 5:
        break
