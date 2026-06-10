"""Find the DTB API endpoint behind the Loading... placeholder."""
import httpx, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9",
}

url = "https://transitobucaramanga.gov.co/dtb/atencion-y-servicios-a-la-ciudadania/pico-y-placa"
r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)

# Search for API endpoints in the HTML
api_patterns = re.findall(r'["\']([^"\']*(?:api|rest|graphql|wp-json|ajax)[^"\']*)["\']', r.text, re.IGNORECASE)
print("=== API endpoints found in HTML ===")
for api in api_patterns[:10]:
    print(f"  {api[:150]}")

# Search for JavaScript files that might contain the API call
js_files = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
print(f"\n=== JS files: {len(js_files)} ===")
for js in js_files[:10]:
    full_url = js if js.startswith("http") else f"https://transitobucaramanga.gov.co{js}" if js.startswith("/") else js
    print(f"  {full_url[:150]}")
    # Try fetching one JS file
    if len(js_files) > 0 and js_files.index(js) == 0:
        try:
            js_url = f"https://transitobucaramanga.gov.co{js}" if js.startswith("/") else js
            js_r = httpx.get(js_url, headers=headers, timeout=10)
            # Search for rotation-related API calls in JS
            api_calls = re.findall(r'["\']([^"\']*(?:pico|placa|rotacion|rotation|restriction)[^"\']*)["\']', js_r.text, re.IGNORECASE)
            if api_calls:
                print(f"    API calls found: {api_calls[:5]}")
        except:
            pass

# Look for data attributes or hidden inputs
data_attrs = re.findall(r'data-[^=]+=["\']([^"\']+)["\']', r.text)
interesting = [d for d in data_attrs if any(w in d.lower() for w in ['api', 'url', 'endpoint', 'source', 'rest'])]
if interesting:
    print(f"\n=== Interesting data attributes ===")
    for d in interesting[:5]:
        print(f"  {d[:150]}")

# Check for WordPress REST API
wp_api = "https://transitobucaramanga.gov.co/wp-json/wp/v2/"
try:
    wr = httpx.get(wp_api, headers=headers, timeout=10)
    print(f"\nWordPress API: {wr.status_code}")
    if wr.status_code == 200:
        print(f"  Available: {wr.text[:200]}")
except Exception as e:
    print(f"\nWordPress API: {e}")

# Try common WordPress custom endpoints
for endpoint in [
    "/wp-json/dtb/v1/pico-y-placa",
    "/wp-json/dtb/v1/rotation",
    "/wp-json/api/v1/pico-y-placa",
    "/api/pico-y-placa",
    "/api/rotation",
]:
    try:
        ep_url = f"https://transitobucaramanga.gov.co{endpoint}"
        er = httpx.get(ep_url, headers=headers, timeout=10)
        if er.status_code != 404:
            print(f"\n{endpoint}: {er.status_code} — {er.text[:200]}")
    except:
        pass
