"""Search for embedded data in JS-rendered sites."""
import httpx, re

headers = {"User-Agent": "Mozilla/5.0"}

r = httpx.get("https://picoyplacaya.com.co/bucaramanga", headers=headers, timeout=15, follow_redirects=True)

# Search for embedded JSON or script data
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"Script tags: {len(scripts)}")
for s in scripts:
    if 'pico' in s.lower() or 'placa' in s.lower() or 'rotation' in s.lower():
        print(f"\nScript with pico/placa ({len(s)} chars):")
        # Just show digit patterns within
        digits_in_script = re.findall(r'\d{1,2}\s*[ye,]\s*\d{1,2}', s)
        if digits_in_script:
            print(f"  Digit pairs: {digits_in_script[:10]}")

# Search for __NEXT_DATA__ or similar
for pattern in [r'__NEXT_DATA__\s*=\s*(\{.*?\});', r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});']:
    matches = re.findall(pattern, r.text[:50000], re.DOTALL)
    if matches:
        print(f"\nFound data blob ({len(matches[0])} chars)")

# Also try the API approach - maybe there's a REST endpoint
api_urls = [
    "https://picoyplacaya.com.co/api/bucaramanga",
    "https://picoyplacaya.com.co/api/rotation/bucaramanga",
    "https://api.picoyplacaya.com.co/bucaramanga",
]
for api in api_urls:
    try:
        ar = httpx.get(api, headers=headers, timeout=10)
        print(f"\n{api}: {ar.status_code} - {ar.text[:200]}")
    except:
        pass
