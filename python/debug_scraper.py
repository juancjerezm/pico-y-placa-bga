"""Debug script: analyze Alcaldia HTML structure."""
import httpx, re
from bs4 import BeautifulSoup

url = "https://bucaramanga.gov.co/noticias/?s=pico+y+placa"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
soup = BeautifulSoup(r.text, "html.parser")

print(f"Status: {r.status_code}, Length: {len(r.text)}")

# Find article containers
for tag in ["article", "div", "li"]:
    items = soup.find_all(tag)
    if len(items) > 3:
        # Look for items with links and headings
        candidates = []
        for item in items:
            a = item.find("a", href=True)
            h = item.find(["h1", "h2", "h3", "h4", "h5"])
            if a and h:
                candidates.append((a, h))
        if candidates:
            print(f"\nFound {len(candidates)} {tag} items with link+heading:")
            for a, h in candidates[:5]:
                print(f"  Link: {a['href'][:100]}")
                print(f"  Title: {h.get_text(strip=True)[:100]}")
            break

# Check for article URLs that need individual fetch
all_links = soup.find_all("a", href=True)
pico_links = [l for l in all_links if "pico" in l.get("href", "").lower() or "pico" in l.get_text().lower()]
print(f"\nPico-related links: {len(pico_links)}")
for l in pico_links[:5]:
    print(f"  {l['href'][:120]}")
    print(f"  Text: {l.get_text(strip=True)[:80]}")

# Try fetching the first article individually
if pico_links:
    article_url = pico_links[0]["href"]
    if not article_url.startswith("http"):
        article_url = "https://bucaramanga.gov.co" + article_url
    print(f"\nFetching individual article: {article_url}")
    ar = httpx.get(article_url, headers=headers, timeout=15, follow_redirects=True)
    print(f"Article status: {ar.status_code}, Length: {len(ar.text)}")
    # Search for digit pairs
    digits = re.findall(r"[5-9]\s*y\s*[0-4]", ar.text)
    print(f"Digit pairs found: {len(digits)}")
    for d in digits[:5]:
        print(f"  {d}")
