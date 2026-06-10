"""Search for Pico y Placa Bucaramanga 2026 via multiple sources."""
import httpx, re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Try Vanguardia with Google site search
try:
    r = httpx.get(
        "https://www.google.com/search?q=site:vanguardia.com+pico+y+placa+bucaramanga+2026+rotación",
        headers=headers, timeout=15
    )
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a", href=True)
    vg_links = [l["href"] for l in links if "vanguardia.com" in l.get("href", "")]
    print("=== Google: vanguardia.com links ===")
    for l in vg_links[:5]:
        # Extract actual URL from Google redirect
        m = re.search(r'(https://www\.vanguardia\.com/[^&"]+)', l)
        if m:
            print(f"  {m.group(1)[:120]}")
except Exception as e:
    print(f"Google search error: {e}")

# Try Google News for Pico y Placa Bucaramanga
try:
    r = httpx.get(
        "https://news.google.com/search?q=pico+y+placa+bucaramanga+2026&hl=es-419",
        headers=headers, timeout=15
    )
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    articles = soup.find_all("article")
    print(f"\n=== Google News: {len(articles)} articles ===")
    for a in articles[:5]:
        text = a.get_text(strip=True)
        if "pico" in text.lower():
            print(f"  {text[:150]}")
except Exception as e:
    print(f"Google News error: {e}")

# Check if there's a known reliable API
print("\n=== Quick summary ===")
print("Best available source: picoyplacaya.com.co (JSON embedded, verified by pattern logic)")
print("DTB: only historical PDFs, current digits loaded via JS")
print("Alcaldía: only announces, doesn't publish digits")
print("Vanguardia: search returns 404, different URL structure")
print("\nRecommendation: Use picoyplacaya as primary, with periodic manual verification against DTB social media")
