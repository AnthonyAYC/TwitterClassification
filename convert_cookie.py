import json

def convert_netscape_to_playwright(netscape_file, output_json):
    cookies = []
    with open(netscape_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            domain, flag, path, secure, expires, name, value = line.strip().split("\t")
            cookies.append({
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "httpOnly": False,
                "secure": secure.lower() == "true",
                "sameSite": "Lax"
            })

    with open(output_json, "w", encoding="utf-8") as out:
        json.dump({"cookies": cookies}, out, indent=4)

convert_netscape_to_playwright("x.com_cookies.txt", "auth.json")