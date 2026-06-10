"""Cross-verify: extract ALL text from DTB page and compare with picoyplacaya."""
import httpx, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9",
}

url = "https://transitobucaramanga.gov.co/dtb/atencion-y-servicios-a-la-ciudadania/pico-y-placa"
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")

# Extract ALL text from ALL elements
all_text = []
for elem in soup.find_all(["p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "span", "div"]):
    t = elem.get_text(strip=True)
    if t and len(t) > 3:
        all_text.append(t)

# Filter for rotation-related content
rotation_lines = [l for l in all_text if any(w in l.lower() for w in [
    "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes",
    "sábado", "sabado", "dígito", "digito", "pico", "placa", "rotación",
    "rotacion", "restringido", "vehículo", "particular"
])]

print("=== DTB — Rotation-related text ===")
for line in rotation_lines:
    print(f"  {line[:150]}")

# Now compare with picoyplacaya data
print("\n=== picoyplacaya.com.co — Current rotation (claimed) ===")
print("  Q2 2026: L 0·1, M 2·3, X 4·5, J 6·7, V 8·9")
print("  Cycle anchor: 2026-04-29")

# Search for the specific digit pairs in DTB text
dtb_text = " ".join(rotation_lines).lower()
picoypairs = [(0,1), (2,3), (4,5), (6,7), (8,9)]
print("\n=== Cross-check: picoyplacaya pairs in DTB text ===")
for d1, d2 in picoypairs:
    found = f"{d1} y {d2}" in dtb_text or f"{d1},{d2}" in dtb_text
    print(f"  {d1} y {d2}: {'✅' if found else '❌'}")

# Also check the "nueva rotación" article from Alcaldía for reference
print("\n=== Alcaldía — 'nueva rotación octubre 2024' (historical reference) ===")
print("  L 7·8, M 9·0, X 1·2, J 3·4, V 5·6")
