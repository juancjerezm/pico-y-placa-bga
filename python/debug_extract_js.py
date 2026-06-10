"""Extract rotation data from embedded JavaScript."""
import httpx, re, json

headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://picoyplacaya.com.co/bucaramanga", headers=headers, timeout=15, follow_redirects=True)

# Find the big script with digit pairs
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
for s in scripts:
    if len(s) > 100000 and 'pico' in s.lower():
        print(f"Big script ({len(s)} chars)")
        # Look for weekday patterns
        for wd in ['lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado']:
            idx = s.lower().find(wd)
            if idx >= 0:
                snippet = s[max(0,idx-20):idx+80]
                # Clean up escape chars
                snippet = snippet.replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                print(f"  {wd}: ...{snippet}...")
        
        # Try to find JSON-like structures with rotation data
        json_matches = re.findall(r'\{[^}]*?(?:lunes|martes|rotacion|rotation|digits|placas)[^}]*\}', s[:50000], re.IGNORECASE)
        for j in json_matches[:5]:
            print(f"  JSON-like: {j[:200]}")
        
        # Look for array of digit pairs
        arrays = re.findall(r'\[(\d+,\d+,\d+,\d+,\d+)\]', s)
        if arrays:
            print(f"  Digit arrays: {arrays[:5]}")
        
        break
