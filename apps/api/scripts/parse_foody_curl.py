"""Parse cURL command to extract Foody API details"""
import sys
import re
import json
from pathlib import Path


def parse_curl(curl_text: str) -> dict:
    """Parse cURL command and extract URL, headers, data"""
    
    # Extract URL
    url_match = re.search(r"curl\s+'([^']+)'", curl_text)
    if not url_match:
        url_match = re.search(r'curl\s+"([^"]+)"', curl_text)
    if not url_match:
        url_match = re.search(r'curl\s+(\S+)', curl_text)
    
    url = url_match.group(1) if url_match else None
    
    # Extract headers
    headers = {}
    for match in re.finditer(r"-H\s+'([^:]+):\s*([^']+)'", curl_text):
        key, value = match.groups()
        headers[key.strip()] = value.strip()
    
    # Also try double quotes
    for match in re.finditer(r'-H\s+"([^:]+):\s*([^"]+)"', curl_text):
        key, value = match.groups()
        headers[key.strip()] = value.strip()
    
    # Extract data (for POST requests)
    data = None
    data_match = re.search(r"--data-raw\s+'([^']+)'", curl_text)
    if not data_match:
        data_match = re.search(r'--data-raw\s+"([^"]+)"', curl_text)
    if data_match:
        try:
            data = json.loads(data_match.group(1))
        except:
            data = data_match.group(1)
    
    return {
        "url": url,
        "headers": headers,
        "data": data
    }


def extract_cookie(parsed: dict) -> str:
    """Extract cookie from headers"""
    headers = parsed["headers"]
    
    for key, value in headers.items():
        if key.lower() == "cookie":
            return value
    
    return None


def generate_python_code(parsed: dict, cookie: str) -> str:
    """Generate Python code to call the API"""
    
    code = f'''"""Foody API Test - Auto-generated"""
import httpx
import asyncio
import json


async def test_foody_api():
    """Test Foody API with captured cookie"""
    
    url = "{parsed["url"]}"
    
    headers = {{
'''
    
    # Add essential headers
    essential_headers = [
        "accept", "accept-language", "content-type",
        "user-agent", "referer", "origin", "x-requested-with"
    ]
    
    for key, value in parsed["headers"].items():
        key_lower = key.lower()
        if key_lower in essential_headers:
            # Escape quotes in value
            value_escaped = value.replace('"', '\\"')
            code += f'        "{key}": "{value_escaped}",\n'
    
    code += '    }\n\n'
    
    # Add cookie loading
    if cookie:
        code += '''    # Load cookie from file (if exists)
    try:
        with open(".foody_cookie", "r") as f:
            cookie_data = json.load(f)
            headers["cookie"] = cookie_data["cookie"]
    except FileNotFoundError:
        print("⚠️  No .foody_cookie file found, using hardcoded cookie")
        print("   Cookie may expire soon!")
    
'''
    
    code += '''    async with httpx.AsyncClient() as client:
        try:
'''
    
    if parsed["data"]:
        code += f'''            response = await client.post(
                url,
                headers=headers,
                json={json.dumps(parsed["data"], indent=16)},
                timeout=30.0
            )
'''
    else:
        code += '''            response = await client.get(
                url,
                headers=headers,
                timeout=30.0
            )
'''
    
    code += '''            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("\\n✅ Success! Response structure:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                
                # Try to find restaurants in response
                if isinstance(data, dict):
                    for key in ["Items", "items", "data", "restaurants", "result", "SearchItems"]:
                        if key in data:
                            items = data[key]
                            if isinstance(items, list):
                                print(f"\\n📍 Found {len(items)} items in '{key}'")
                                if items:
                                    print("\\nFirst item:")
                                    print(json.dumps(items[0], indent=2, ensure_ascii=False))
                                break
            else:
                print(f"\\n❌ Error: {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"\\n❌ Exception: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_foody_api())
'''
    
    return code


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_foody_curl.py <curl_file.txt>")
        print("\nOr paste cURL directly:")
        print("python parse_foody_curl.py -")
        return
    
    # Read cURL from file or stdin
    if sys.argv[1] == "-":
        print("Paste cURL command (Ctrl+D when done):")
        curl_text = sys.stdin.read()
    else:
        curl_file = Path(sys.argv[1])
        if not curl_file.exists():
            print(f"❌ File not found: {curl_file}")
            return
        curl_text = curl_file.read_text(encoding="utf-8")
    
    print("="*60)
    print("  PARSING cURL COMMAND")
    print("="*60)
    
    # Parse
    parsed = parse_curl(curl_text)
    cookie = extract_cookie(parsed)
    
    # Display results
    print(f"\n📍 URL:")
    print(f"   {parsed['url']}")
    
    if cookie:
        print(f"\n🍪 Cookie:")
        display_cookie = cookie[:80] + "..." if len(cookie) > 80 else cookie
        print(f"   {display_cookie}")
    
    print(f"\n📋 Headers ({len(parsed['headers'])} total):")
    for key in list(parsed['headers'].keys())[:5]:
        if key.lower() != "cookie":  # Don't display cookie twice
            value = parsed['headers'][key]
            display_value = value[:40] + "..." if len(value) > 40 else value
            print(f"   {key}: {display_value}")
    if len(parsed['headers']) > 5:
        print(f"   ... and {len(parsed['headers']) - 5} more")
    
    if parsed['data']:
        print(f"\n📦 Request Data:")
        print(f"   {json.dumps(parsed['data'], indent=2)[:200]}")
    
    # Save cookie to file
    if cookie:
        cookie_data = {
            "cookie": cookie,
            "url": parsed["url"]
        }
        
        with open(".foody_cookie", "w") as f:
            json.dump(cookie_data, f, indent=2)
        
        print(f"\n✅ Saved cookie to .foody_cookie")
    
    # Generate test script
    test_code = generate_python_code(parsed, cookie)
    
    with open("test_foody_api.py", "w", encoding="utf-8") as f:
        f.write(test_code)
    
    print(f"\n✅ Generated test_foody_api.py")
    print(f"\nNext steps:")
    print(f"  1. Run: python test_foody_api.py")
    print(f"  2. If successful, update foody.py with the working endpoint")
    print("="*60)


if __name__ == "__main__":
    main()