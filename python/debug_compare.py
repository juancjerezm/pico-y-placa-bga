"""Compare Pico y Placa data sources."""
import httpx, re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0"}

sources = [
    ("picoyplacaya.com.co", "https://picoyplacaya.com.co/bucaramanga"),
    ("pyphoy.com", "https://www.pyphoy.com/bucaramanga/motos/1"),
]

for name, url in sources:
    print(f"\n=== {name} ===")
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        print(f"Status: {r.status_code}, Length: {len(r.text)}")
        
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n", strip=True)
        
        # Digit pairs
        pairs = re.findall(r"(\d)\s*y\s*(\d)", text)
        print(f"Digit pairs: {len(pairs)}")
        for d in pairs[:8]:
            print(f"  {d[0]} y {d[1]}")
        
        # Weekday matches
        wd = re.findall(r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[^.]*?(\d)\s*y\s*(\d)", text, re.IGNORECASE)
        print(f"Weekday matches: {len(wd)}")
        for w in wd:
            print(f"  {w[0]}: {w[1]} y {w[2]}")
        
        # Date mentions
        dates = re.findall(r"(\d{1,2}\s+de\s+\w+\s+(?:de\s+)?\d{4})", text, re.IGNORECASE)
        print(f"Dates: {dates[:3]}")
        
        # Look for current quarter info
        q = re.findall(r"(2026|actual|vigente|rotación).{0,50}", text[:5000], re.IGNORECASE)
        if q:
            print(f"Relevant: {q[0][:100]}")
    except Exception as e:
        print(f"Error: {e}")
