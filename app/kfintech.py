import re
import base64
import urllib.parse

import requests
from bs4 import BeautifulSoup
from Crypto.Cipher  import AES
from Crypto.Util.Padding import pad, unpad
from PIL             import Image
from io              import BytesIO
from captcha import predict_captcha
#     img.save("C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\captcha.png")

# predict = predict_captcha(None, 'kfintech')
# print(predict)

BASE = "https://rti.kfintech.com/ipostatus/"

def aes_encrypt(plain_text: str, key_str: str) -> str:
    """Encrypts the given plain text using AES-128-CBC with the provided key."""
    key = key_str.encode('utf-8')  # Convert key to bytes
    iv = key  # Using key as IV (not recommended for security, but matching given logic)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_text = pad(plain_text.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_text)
    
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def aes_decrypt(encrypted_base64: str, key_str: str) -> str:
    """Decrypts the given Base64-encoded AES-128-CBC ciphertext using the provided key."""
    key = key_str.encode('utf-8')
    iv = key  # Using key as IV
    
    encrypted_bytes = base64.b64decode(encrypted_base64)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    
    return decrypted_bytes.decode('utf-8')


def aes_encrypt(plain_text: str, key_str: str) -> str:
    """
    AES‑128‑CBC encrypt & base64‑encode, using key_str both as key and IV.
    (Matches kfintech’s JS logic.)
    """
    key = key_str.encode('utf‑8')
    iv  = key
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plain_text.encode('utf‑8'), AES.block_size))
    return base64.b64encode(ct).decode()

def solve_captcha(session: requests.Session, img_url: str) -> str:
    """
    Download the one‑time CAPTCHA and OCR it with Tesseract.
    """
    r = session.get(img_url)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content))
    # Tesseract psm=8 is good for single words
    img.save("C:\\Users\\kavya\\Documents\\My_programming\\buy-sell\\myflaskapp\\app\\captcha.png")

    predict = predict_captcha(None, 'kfintech')
    print(predict)
    return  predict

# 3) Main flow
def fetch_status(ipo_val, pan):
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    })

    # GET landing page
    r = s.get(BASE); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # one‑time token
    onclk = soup.find("a", id="btn_submit_query")["onclick"]
    token = re.search(r"validate_all\('([^']+)'\)", onclk).group(1)

    # ASP.NET hidden fields
    vs = soup.find(id="__VIEWSTATE")         ["value"]
    vg = soup.find(id="__VIEWSTATEGENERATOR")["value"]
    ev = soup.find(id="__EVENTVALIDATION")   ["value"]

    # CAPTCHA
    cap_url = urllib.parse.urljoin(BASE, soup.find(id="captchaimg")["src"])
    captcha = solve_captcha(s, cap_url)
    print("Captcha:", captcha)

    # encrypt PAN
    pan_enc = aes_encrypt(pan, token)

    # POST form
    data = {
      "__EVENTTARGET":        "btn_submit_query",
      "__EVENTARGUMENT":      "",
      "__LASTFOCUS":          "",
      "__VIEWSTATE":          vs,
      "__VIEWSTATEGENERATOR": vg,
      "__EVENTVALIDATION":    ev,

      "ddl_ipo":         ipo_val,
      "query":           "pan",
      "txt_pan":         pan_enc,
      "txt_captcha":     captcha,
      "_h_query":        "pan",
      "encrypt_payload": "Y",
      "req_src":         "",
    }
    post = s.post(BASE, data=data)
    post.raise_for_status()
    return post.text


# 4) Parse out the result
def parse_result(html: str):
    soup = BeautifulSoup(html, "html.parser")
    print(soup.prettify())
    no_results = soup.select_one("#grid_results td .badge.bg-danger")
    if no_results:
        return {"status":"Not Allotted"}
    card = soup.select_one("#grid_results .result-card .card-body")
    out = {}
    for row in card.select(".successtxt2 .qvalue"):
        # they come in order: appl no, name, client id, pan, applied, allotted
        # you can map them however you like
        print(row.get_text(strip=True))
    return out

if __name__ == "__main__":
    # 1) Copy‑paste exactly an <option> value from the page’s IPO dropdown:
    ddl = "ANTB~AnthemBio~0~17/07/2025~17/07/2025~EQT"
    pan = "OMOPS4188F"

    html = fetch_status(ddl, pan)
    print(parse_result(html))