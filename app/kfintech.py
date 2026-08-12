import requests
try:
    from app.tor import make_request_through_tor
except ImportError:
    from tor import make_request_through_tor
import json
import re
import difflib
import os
from urllib.parse import quote_plus, urljoin

API_URL = "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/prod/api/query"

# cache for client list
_CLIENT_LIST = None

def fetch_client_list(js_url=None, local_json_path=None):
    """Return a list of client dicts with keys 'clientId' and 'name'.
    Tries in order:
    - load local JSON file if provided/exists
    - fetch and parse the KFintech JS file
    Returns list or empty list on failure.
    """
    global _CLIENT_LIST
    if _CLIENT_LIST is not None:
        return _CLIENT_LIST

    # try local JSON first
    if local_json_path and os.path.exists(local_json_path):
        try:
            with open(local_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _CLIENT_LIST = data
                return _CLIENT_LIST
        except Exception:
            pass

    # determine js_url: use provided, else try to discover current main.*.js from homepage
    if not js_url:
        try:
            home = requests.get("https://ipostatus.kfintech.com/", timeout=10)
            home.raise_for_status()
            # try to find a script tag with src containing /static/js/main.<hash>.js
            m = re.search(r"src=[\'\"]([^\'\"]*?/static/js/main\.[^\'\"]+\.js)[\'\"]", home.text)
            if m:
                js_url = m.group(1)
                if js_url.startswith("/"):
                    js_url = "https://ipostatus.kfintech.com" + js_url
            else:
                # fallback: search for any main.<hash>.js occurrence
                m2 = re.search(r"(/static/js/main\.[^\'\"\s>]+\.js)", home.text)
                if m2:
                    js_url = "https://ipostatus.kfintech.com" + m2.group(1)
                else:
                    # last-resort fallback to a previously-seen filename
                    js_url = "https://ipostatus.kfintech.com/static/js/main.fe1258b3.js"
        except Exception:
            # network or parsing error: fall back to provided js_url or known filename
            js_url = js_url or "https://ipostatus.kfintech.com/static/js/main.fe1258b3.js"

    # Normalize relative script URLs (e.g. './static/js/main.e2d1ff44.js')
    base_host = "https://ipostatus.kfintech.com/"
    js_url = (js_url or "").strip()
    if js_url.startswith("//"):
        js_url = "https:" + js_url
    if not js_url.lower().startswith("http"):
        js_url = urljoin(base_host, js_url)

    print(f"Fetching client-list JS from: {js_url}")
    try:
        r = requests.get(js_url, timeout=15)
        r.raise_for_status()
        js_text = r.text
        # First, try to find JSON.parse('...') or JSON.parse("...") that embeds the client-list
        m_jsonparse = re.search(r"JSON\.parse\(\s*['\"](\s*\[\s*\{[^\]]*?clientId[^\]]*?\]\s*)['\"]\s*\)", js_text, re.DOTALL)
        if m_jsonparse:
            candidate = m_jsonparse.group(1)
            try:
                # unescape common JS escapes inside the string literal
                candidate = candidate.encode('utf-8').decode('unicode_escape')
            except Exception:
                # if unescape fails, proceed with the raw candidate
                pass
        else:
            # find an array of objects containing clientId
            m = re.search(r"(\[\s*\{[^\]]*?clientId[^\]]*?\])", js_text, re.DOTALL)
            if not m:
                # fallback scanning around clientId
                idx = js_text.find('clientId')
                if idx == -1:
                    return []
                start = js_text.rfind('[', 0, idx)
                end = js_text.find(']', idx)
                if start == -1 or end == -1:
                    return []
                candidate = js_text[start:end+1]
            else:
                candidate = m.group(1)

        # try to load as JSON
        try:
            data = json.loads(candidate)
        except Exception:
            # remove trailing commas and try again
            cleaned = re.sub(r",\s*\]", "]", candidate)
            cleaned = cleaned.replace("'", '"')
            data = json.loads(cleaned)

        # normalize entries to have clientId and name
        clients = []
        for item in data:
            cid = item.get('clientId') or item.get('clientid') or item.get('clientID')
            name = item.get('name') or item.get('label') or item.get('company')
            if cid and name:
                clients.append({'clientId': str(cid), 'name': name.strip()})

        _CLIENT_LIST = clients
        return _CLIENT_LIST
    except Exception:
        return []


def get_client_id_for_ipo(ipo_name, cutoff=0.6):
    """Fuzzy-match `ipo_name` against the client list and return the clientId (string).
    Returns None if no good match is found.
    """
    if not ipo_name:
        return None
    clients = fetch_client_list()
    print(f"Matching IPO name '{ipo_name}' against {(clients)} clients")
    if not clients:
        return None
    names = [c['name'] for c in clients]
    # use difflib to find best match
    matches = difflib.get_close_matches(ipo_name, names, n=3, cutoff=cutoff)
    if matches:
        best = matches[0]
        for c in clients:
            if c['name'] == best:
                return c['clientId']
    # try case-insensitive substring match
    ipo_upper = ipo_name.strip().upper()
    for c in clients:
        if ipo_upper in c['name'].upper() or c['name'].upper() in ipo_upper:
            return c['clientId']
    return None


def query_pan_status_tor(pan_list, client_id=None, ipo_name=None):
    """
    Query PAN status for a list of PANs using the new KFintech API, with Tor integration.
    Returns a dict mapping PAN to response JSON or error.
    """
    results = {}

    def _safe_int(value):
        try:
            return int(float(value or 0))
        except Exception:
            return 0

    for pan in pan_list:
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "access-control-allow-origin": "*",
            "client_id": client_id or None,
            "origin": "https://ipostatus.kfintech.com",
            "priority": "u=1, i",
            "referer": "https://ipostatus.kfintech.com/",
            "reqparam": pan,
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        }
        session = requests.Session()
        try:
            tor = True
            if tor:
                # make_request_through_tor does not accept `params`, so embed them in the URL
                q = f"type=pan&reqparam={quote_plus(pan)}"
                url = f"{API_URL}?{q}"
                response = make_request_through_tor(session, url, headers=headers)
            else:
                response = session.get(API_URL, headers=headers, params={"type": "pan", "reqparam": pan})
            # print(f"PAN: {pan} => Status Code: {response.status_code}")
            # print(f"Response Text: {response.text}")
            if response.status_code == 200:
                try:
                    json_resp = response.json()
                    # If the API returns {'data': [ {...} ]}, flatten to the inner dict
                    if isinstance(json_resp, dict) and 'data' in json_resp and isinstance(json_resp['data'], list) and len(json_resp['data']) > 0 and isinstance(json_resp['data'][0], dict):
                        # Use local variable for clearer ref
                        data_list = json_resp['data']

                        try:
                            if ipo_name and "sbi" in ipo_name.lower():
                                # SBI shareholder special: keep 37-share records after the others,
                                # and still push 90-share records toward the bottom of the non-37 group.
                                data_list.sort(key=lambda x: (
                                    1 if _safe_int(x.get('All_Shares')) == 37 else 0,
                                    1 if _safe_int(x.get('App_Shares')) == 90 else 0,
                                    _safe_int(x.get('App_Shares'))
                                ))
                            else:
                                # Default: keep 37-share records after the others.
                                data_list.sort(key=lambda x: (
                                    1 if _safe_int(x.get('All_Shares')) == 37 else 0,
                                    _safe_int(x.get('App_Shares'))
                                ))
                        except Exception as e:
                            print(f"Error sorting data list: {e}")

                        # Start with the first data record (after sorting)
                        flat = dict(data_list[0])
                        
                        # Check for additional records and flatten them
                        if len(data_list) > 1:
                            for idx, record in enumerate(data_list[1:], start=2):
                                if isinstance(record, dict):
                                    for rk, rv in record.items():
                                        flat[f"{rk}_{idx}"] = rv
                        
                        # Merge other top-level keys if they are not 'data' and not duplicated
                        for k, v in json_resp.items():
                            if k == 'data':
                                continue
                            if k not in flat:
                                flat[k] = v
                            else:
                                # avoid overwriting keys from data; prefix if needed
                                flat[f"top_{k}"] = v
                        results[pan] = flat
                    elif isinstance(json_resp, dict):
                        # Already a dict but no 'data' list; use as-is
                        results[pan] = json_resp
                    else:
                        # Unexpected structure; store raw text
                        results[pan] = {"text": response.text}
                except Exception:
                    results[pan] = {"error": "Invalid JSON", "text": response.text}
            else:
                results[pan] = {"error": f"HTTP {response.status_code}", "text": response.text}
        except Exception as e:
            results[pan] = {"error": str(e)}
            print(f"PAN: {pan} => Error: {e}")
    return results


def print_client_list(ipo_name=None):
    """Print fetched clientId/name pairs and optionally fuzzy-match an IPO name.

    Returns the list of clients (list of dicts). If ipo_name is provided, also
    prints the best fuzzy-match clientId.
    """
    clients = fetch_client_list()
    best = None
    if ipo_name:
        best = get_client_id_for_ipo(ipo_name)
        if best:
            print(f"Best match for IPO '{ipo_name}': clientId={best}")
        else:
            print(f"No clientId match found for IPO '{ipo_name}'")

    print(f"Total clients fetched: {len(clients)}")
    for c in clients:
        print(f"clientId={c['clientId']}\tname={c['name']}")

    return clients if not ipo_name else (clients, best)

# Example usage
if __name__ == "__main__":
    import sys

    # If an argument is provided, treat it as an IPO name to fuzzy-match
    if len(sys.argv) > 1:
        ipo_name = " ".join(sys.argv[1:]).strip()
        cid = get_client_id_for_ipo(ipo_name)
        if cid:
            print(f"Best match for IPO '{ipo_name}': clientId={cid}")
        else:
            print(f"No clientId match found for IPO '{ipo_name}'")
        # Also print the full client list for debugging
        clients = fetch_client_list()
        print(f"\nTotal clients fetched: {len(clients)}")
        for c in clients:
            print(f"clientId={c['clientId']}	name={c['name']}")
    else:
        # No args: print all clientId and company names
        clients = fetch_client_list()
        print(f"Total clients fetched: {len(clients)}")
        for c in clients:
            print(f"clientId={c['clientId']}	name={c['name']}")
        # Example PAN query left commented for convenience
        # pan_list = ["OMOPS4188F"]  # Add more PANs as needed
        # print(query_pan_status_tor(pan_list))