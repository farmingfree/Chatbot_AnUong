"""Parse cURL command to extract ShopeeFood API details"""
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


def extract_auth_info(parsed: dict) -> dict:
    """Extract authentication related info"""
    headers = parsed["headers"]
    
    auth_info = {
        "access_token": None,
        "client_id": None,
        "app_type": None,
        "cookie": None,
        "authorization": None
    }
    
    # Check various auth header patterns
    for key, value in headers.items():
        key_lower = key.lower()
        
        if "access-token" in key_lower or "x-foody-access-token" in key_lower:
            auth_info["access_token"] = value
        elif "client-id" in key_lower or "x-foody-client-id" in key_lower:
            auth_info["client_id"] = value
        elif "app-type" in key_lower or "x-foody-app-type" in key_lower:
            auth_info["app_type"] = value
        elif key_lower == "cookie":
            auth_info["cookie"] = value
        elif key_lower == "authorization":
            auth_info["authorization"] = value
    
    return auth_info


def generate_python_code(parsed: dict, auth_info: dict) -> str:
    """Generate Python code to call the API"""
    
    code = f'''"""ShopeeFood API Test - Auto-generated"""
import httpx
import asyncio
import json


async def test_shopee_api():
    """Test ShopeeFood API with captured headers"""
    
    url = "{parsed["url"]}"
    
    headers = {{
'''
    
    # Add essential headers
    essential_headers = [
        "accept", "accept-language", "content-type",
        "user-agent", "referer", "origin"
    ]
    
    for key, value in parsed["headers"].items():
        key_lower = key.lower()
        if key_lower in essential_headers or "x-foody" in key_lower or "authorization" in key_lower:
            # Escape quotes in value
            value_escaped = value.replace('"', '\\"')
            code += f'        "{key}": "{value_escaped}",\n'
    
    code += '    }\n\n'
    
    # Add auth token loading
    if auth_info["access_token"]:
        code += '''    # Load token from file (if exists)
    try:
        with open(".shopee_token", "r") as f:
            token_data = json.load(f)
            headers["x-foody-access-token"] = token_data["access_token"]
            if "client_id" in token_data:
                headers["x-foody-client-id"] = token_data["client_id"]
    except FileNotFoundError:
        print("⚠️  No .shopee_token file found, using hardcoded token")
        print("   Token may expire soon!")
    
'''
    
    if auth_info["cookie"]:
        code += '''    # Add cookies
    cookies = {}
    for cookie in headers.get("cookie", "").split("; "):
        if "=" in cookie:
            k, v = cookie.split("=", 1)
            cookies[k] = v
    
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
                    for key in ["items", "data", "restaurants", "result", "reply"]:
                        if key in data and isinstance(data[key], list):
                            print(f"\\n📍 Found {len(data[key])} items in '{key}'")
                            if data[key]:
                                print("\\nFirst item:")
                                print(json.dumps(data[key][0], indent=2, ensure_ascii=False))
                            break
            else:
                print(f"\\n❌ Error: {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"\\n❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_shopee_api())
'''
    
    return code


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_shopee_curl.py <curl_file.txt>")
        print("\nOr paste cURL directly:")
        print("python parse_shopee_curl.py")
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
    auth_info = extract_auth_info(parsed)
    
    # Display results
    print(f"\n📍 URL:")
    print(f"   {parsed['url']}")
    
    print(f"\n🔑 Authentication Info:")
    for key, value in auth_info.items():
        if value:
            display_value = value[:50] + "..." if len(value) > 50 else value
            print(f"   {key}: {display_value}")
    
    print(f"\n📋 Headers ({len(parsed['headers'])} total):")
    for key in list(parsed['headers'].keys())[:5]:
        value = parsed['headers'][key]
        display_value = value[:40] + "..." if len(value) > 40 else value
        print(f"   {key}: {display_value}")
    if len(parsed['headers']) > 5:
        print(f"   ... and {len(parsed['headers']) - 5} more")
    
    if parsed['data']:
        print(f"\n📦 Request Data:")
        print(f"   {json.dumps(parsed['data'], indent=2)[:200]}")
    
    # Save token to file
    if auth_info["access_token"] or auth_info["authorization"]:
        token_data = {
            "access_token": auth_info["access_token"] or auth_info["authorization"],
            "client_id": auth_info["client_id"],
            "app_type": auth_info["app_type"],
            "cookie": auth_info["cookie"]
        }
        
        with open(".shopee_token", "w") as f:
            json.dump(token_data, f, indent=2)
        
        print(f"\n✅ Saved token to .shopee_token")
    
    # Generate test script
    test_code = generate_python_code(parsed, auth_info)
    
    with open("test_shopee_api.py", "w", encoding="utf-8") as f:
        f.write(test_code)
    
    print(f"\n✅ Generated test_shopee_api.py")
    print(f"\nNext steps:")
    print(f"  1. Run: python test_shopee_api.py")
    print(f"  2. If successful, update shopee_food.py with the working endpoint")
    print("="*60)


if __name__ == "__main__":
    main()