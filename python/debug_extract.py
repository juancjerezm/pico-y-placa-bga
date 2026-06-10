"""Debug: test rotation extraction on a known article."""
import httpx, re
from scraper.scraper import extract_rotation_digits, extract_date_range, extract_saturday_calendar
from bs4 import BeautifulSoup

url = "https://www.bucaramanga.gov.co/noticias/nueva-rotacion-de-pico-y-placa-en-bucaramanga-inicia-hoy/"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

soup = BeautifulSoup(r.text, "html.parser")
article = soup.find("article") or soup.find(class_=re.compile("content|entry|post|body", re.I)) or soup
text = article.get_text("\n", strip=True)

digits = extract_rotation_digits(text)
print(f"Digits: {digits}")

dates = extract_date_range(text)
print(f"Date range: {dates}")

# Manually search for dates
iso_dates = re.findall(r"(\d{4}-\d{2}-\d{2})", text)
print(f"ISO dates: {iso_dates}")

spanish_dates = re.findall(r"(\d{1,2}\s+de\s+\w+\s+(?:al|hasta)\s+\d{1,2}\s+de\s+\w+\s+(?:de\s+)?\d{4})", text, re.IGNORECASE)
print(f"Spanish date ranges: {spanish_dates}")

# Any date-like patterns
any_dates = re.findall(r"(\d{1,2}\s+de\s+\w+)", text, re.IGNORECASE)
print(f"Date mentions: {any_dates[:5]}")

sat = extract_saturday_calendar(text)
print(f"Saturday calendar: {sat}")
