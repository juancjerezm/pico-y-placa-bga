"""Try WordPress AJAX endpoint for DTB rotation data."""
import httpx, re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-CO,es;q=0.9",
}

# WordPress AJAX URL
ajax_url = "https://transitobucaramanga.gov.co/dtb/wp-admin/admin-ajax.php"

# Try common WordPress actions for loading content
actions = [
    {"action": "load_pico_y_placa"},
    {"action": "get_rotation"},
    {"action": "get_pico_placa"},
    {"action": "dtb_rotation"},
    {"action": "pico_y_placa_data"},
    {"action": "get_restriction"},
    {"action": "avada_load_content", "post_id": "2014"},  # Fusion/Avada theme
    {"action": "fusion_load_content", "post_id": "2014"},
]

for params in actions:
    try:
        r = httpx.post(ajax_url, data=params, headers=headers, timeout=10)
        if r.status_code == 200 and len(r.text) > 20:
            # Check if response has digit pairs
            pairs = re.findall(r"(\d)\s*y\s*(\d)", r.text)
            if pairs:
                print(f"\n{params['action']}: {r.status_code} — {len(r.text)} chars")
                print(f"  Pairs: {pairs[:5]}")
                print(f"  Preview: {r.text[:300]}")
    except Exception as e:
        pass

# Also try fetching the page with post_id as a parameter
try:
    r = httpx.get("https://transitobucaramanga.gov.co/dtb/atencion-y-servicios-a-la-ciudadania/pico-y-placa/?post_id=2014&action=render", headers=headers, timeout=10)
    print(f"\nDirect render: {r.status_code}")
except:
    pass

# Try the Avada theme's fusion endpoint
try:
    r = httpx.get("https://transitobucaramanga.gov.co/dtb/wp-json/fusion/v1/", headers=headers, timeout=10)
    print(f"\nFusion API: {r.status_code}")
    if r.status_code == 200:
        print(f"  {r.text[:200]}")
except:
    pass

print("\n=== Summary ===")
print("DTB uses WordPress + Avada theme. Rotation loaded via shortcode/AJAX.")
print("Finding the exact AJAX action requires reverse-engineering the Avada theme.")
print("Alternative: picoyplacaya scrapes the DTB and republishes. Their data IS the DTB data.")
