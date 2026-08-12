from urllib.parse import urljoin
import difflib
import re

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.purvashare.com/investor-service/ipo-query"


def _extract_form(soup):
    form = soup.find("form", id="ipo-query")
    if form is None:
        form = soup.find("form")
    return form


def _first_company_id(form):
    if form is None:
        return None

    company_options = []
    for option in form.select('select[name="company_id"] option'):
        value = option.get("value")
        if value:
            company_options.append((value, option.get_text(strip=True)))

    if company_options:
        print("Available companies:")
        for value, label in company_options:
            print(f"- {value}: {label}")
        return company_options[0][0]

    return None


def _normalize_label(label):
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def fetch_company_options():
    session = requests.Session()
    response = session.get(BASE_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    form = _extract_form(soup)
    if form is None:
        return []

    company_options = []
    for option in form.select('select[name="company_id"] option'):
        value = option.get("value")
        label = option.get_text(" ", strip=True)
        if value:
            company_options.append({"company_id": str(value), "name": label})
    return company_options


def purva_company(company_name=None):
    company_options = fetch_company_options()
    if not company_options:
        print("No company options were found for Purva.")
        return None

    if not company_name:
        print("Available companies:")
        for option in company_options:
            print(f"- {option['company_id']}: {option['name']}")
        return company_options[0]["company_id"]

    company_name = company_name.strip().upper()
    names = [option["name"] for option in company_options]

    matches = difflib.get_close_matches(company_name, names, n=1, cutoff=0.4)
    if matches:
        match_name = matches[0]
        for option in company_options:
            if option["name"] == match_name:
                return option["company_id"]

    for option in company_options:
        if company_name in option["name"].upper() or option["name"].upper() in company_name:
            return option["company_id"]

    print(f"Company name '{company_name}' not found in the Purva response.")
    return None


def _extract_result_message(soup):
    selectors = [
        ".alert",
        ".error",
        ".text-danger",
        ".invalid-feedback",
        ".results-section .message",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text

    page_text = soup.get_text(" ", strip=True)
    for needle in ("no record", "no data", "not found", "invalid", "error"):
        if needle in page_text.lower():
            sentence_match = re.search(r"[^.?!]*(no record found[^.?!]*[.?!]?)", page_text, re.IGNORECASE)
            if sentence_match:
                return sentence_match.group(1).strip()
            sentence_match = re.search(r"[^.?!]*(no data[^.?!]*[.?!]?)", page_text, re.IGNORECASE)
            if sentence_match:
                return sentence_match.group(1).strip()
            sentence_match = re.search(r"[^.?!]*(not found[^.?!]*[.?!]?)", page_text, re.IGNORECASE)
            if sentence_match:
                return sentence_match.group(1).strip()
            return needle.title()
    return None


def _extract_result_rows(soup):
    tables = soup.select(".results-section table, table")
    for table in tables:
        headers = []
        header_row = table.find("tr")
        if header_row is None:
            continue

        header_cells = header_row.find_all(["th", "td"])
        for cell in header_cells:
            header_text = cell.get_text(" ", strip=True)
            if header_text:
                headers.append(_normalize_label(header_text))

        rows = []
        for row in table.find_all("tr")[1:]:
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if not cells:
                continue
            row_data = {}
            for index, cell_value in enumerate(cells):
                key = headers[index] if index < len(headers) and headers[index] else f"column_{index + 1}"
                row_data[key] = cell_value
            if row_data:
                rows.append(row_data)

        if rows:
            return rows
    return []


def search_on_pan(company_id, pan, application_number=""):
    session = requests.Session()

    response = session.get(BASE_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    form = _extract_form(soup)

    if form is None:
        print("No allotment form was found on the Purva page.")
        return None

    action = urljoin(BASE_URL, form.get("action") or BASE_URL)
    method = (form.get("method") or "GET").upper()

    csrf_input = form.find("input", {"name": "csrfmiddlewaretoken"})
    csrf_token = csrf_input.get("value") if csrf_input else None

    if company_id is None:
        company_id = _first_company_id(form)

    payload = {
        "company_id": company_id or "",
        "applicationNumber": application_number,
        "panNumber": pan,
    }

    if method == "GET":
        if csrf_token:
            payload["csrfmiddlewaretoken"] = csrf_token
        result = session.get(action, params=payload, timeout=30)
    else:
        if csrf_token:
            payload["csrfmiddlewaretoken"] = csrf_token
        headers = {"Referer": BASE_URL}
        result = session.post(action, data=payload, headers=headers, timeout=30)

    result.raise_for_status()
    return result.text


def purva_pan(company_id, pan, application_number=""):
    try:
        html = search_on_pan(company_id, pan, application_number=application_number)
        soup = BeautifulSoup(html, "html.parser")

        error_message = _extract_result_message(soup)
        if error_message:
            return {
                "pan": pan,
                "company_id": company_id,
                "application_number": application_number,
                "status": "error",
                "error": error_message,
            }

        result_rows = _extract_result_rows(soup)
        if result_rows:
            first_row = result_rows[0]
            result = {
                "pan": pan,
                "company_id": company_id,
                "application_number": application_number,
                "status": "success",
                "error": None,
            }
            result.update(first_row)
            return result

        return {
            "pan": pan,
            "company_id": company_id,
            "application_number": application_number,
            "status": "success",
            "error": None,
            "message": "No structured result table found in response",
        }
    except Exception as exc:
        return {
            "pan": pan,
            "company_id": company_id,
            "application_number": application_number,
            "status": "error",
            "error": str(exc),
        }


if __name__ == "__main__":
    company_id = purva_company()
    print(f"Selected company_id: {company_id}")
    print(search_on_pan(company_id, ""))