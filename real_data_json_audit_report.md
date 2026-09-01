# 📊 Empirical Data Audit & Analysis of Real Scraped IPO Responses (`json/` Directory Audit)

---

## 📌 1. Executive Summary & Audit Overview

An audit of all 6 historical IPO response dump files in the `json/` directory (`Symbiotec.json`, `tempsens.json`, `gaja.json`, `annu.json`, `anu.json`, `sunshine.json`) was conducted:

- **Total Scraped PAN Records Analyzed**: **264 records**
- **Successful API Parsings**: **115 records** (43.6%)
- **Failed / Error Records**: **149 records** (56.4%)

```
Total Scraped Records (264)
├── Successful Records: 115 (43.6%)
└── Error Records: 149 (56.4%)
    ├── KeyError 'd' Crash: 107 (71.8% of errors)
    ├── HTTP 404 / Endpoint Error: 41 (27.5% of errors)
    └── Record Not Found: 1 (0.7% of errors)
```

This high error rate (**56.4%**) demonstrates that **relying solely on transient file dumps without storing raw JSON payloads in the database creates massive data loss and silent failures**.

---

## 🚨 2. Breakdown of Failure Patterns Discovered in Real Data

### A. KeyError `'d'` Crash (107 Records in `sunshine.json`)
* **Symptom**: All 107 records in `sunshine.json` failed with `"error": "'d'"`.
* **Root Cause**: The code assumed that all Bigshare/LinkIntime JSON responses would contain a top-level key `'d'` (`json_data['d']`). When the registrar API returned an error response or a different JSON structure (without `'d'`), `json_data['d']` threw a Python `KeyError: 'd'`, masking the true underlying registrar error!

### B. HTTP 404 & Endpoint Failures (41 Records in `anu.json` & `annu.json`)
* **Symptom**: 41 records returned `{"error": "HTTP 404", "text": "{\"error\":\"Record Not Found\"}"}`.
* **Root Cause**: The API endpoint or parameters were invalid, or the IPO company ID lookup selected a non-existent company ID, returning a 404 from the server gateway.

### C. Missing / Unmatched Records (1 Record in `Symbiotec.json`)
* **Symptom**: Returned `{"Error": "No record found"}` for valid PAN `ABVFA3322P`.

---

## 🔍 3. Empirical Schema Analysis Across Registrars

By inspecting successful records in `json/Symbiotec.json`, `json/gaja.json`, `json/tempsens.json`, and `json/annu.json`, we uncovered the **actual raw fields** returned by registrars:

### Link Intime / MUFG Real Field Schema (`Symbiotec.json`, `gaja.json`)
| Raw Key | Description | Example Values |
| :--- | :--- | :--- |
| `NAME1` | Primary Applicant Name | `"PRIYANK D SANGHAVI"`, `"Jyoti Shrenikkumar Shah"` |
| `DPCLITID` | 16-Digit DP + Client ID | `"1204150001328841"`, `"IN30311611098552"` |
| `ALLOT` | Allotted Share Quantity | `"0"`, `"15"`, `"151"`, `"210"` |
| `SHARES` | Applied Share Quantity | `"15"`, `"93"`, `"210"`, `"1020"` |
| `PEMNDG` | Investor Category | `"Retail"`, `"HNI"` |
| `RFNDNO` | Bank Refund Transaction Reference | `"6712730"`, `"3269425"` |
| `RFNDAMT` | Refund Amount (in INR) | `"14820"`, `"207480"`, `"1007760"` |
| `AMTADJ` | Amount Adjusted for Shares (in INR) | `"0"`, `"14820"`, `"207480"` |
| `BNKCODE` | Bank Identifier Code | `"904"`, `"703"`, `"968"`, `"915"` |
| `match` | Allotment Match Indicator | `"Y"` (Present when shares allotted) |
| `pull` | Data Pull Status | `"X"` |

### KFintech Real Field Schema (`tempsens.json`, `annu.json`)
| Raw Key | Description | Example Values |
| :--- | :--- | :--- |
| `Name` | Applicant Name | `"MRS KALAVATIBEN DINESHCHANDRA SANGHVI"` |
| `Pan_No` | Applicant PAN | `"ADOPS3545D"` |
| `Appln_No` | Application Reference Number | `"229000039949192"`, `"GROWW1c297b8d723"` |
| `DP_CLID` | Demat ID | `"1204150000521287"` |
| `App_Shares` | Applied Quantity | `"3350"`, `"700"`, `"50"` |
| `All_Shares` | Allotted Quantity | `"0"`, `"151"` |

---

## 💡 4. Why Database Storage (`raw_response`) is Essential

1. **Prevents Data Loss**: Storing the raw JSON payload in `TransactionPan.raw_response` ensures that if a parser crashes (e.g. KeyError `'d'`), the raw response from the registrar is preserved in the database for debugging and historical reprocessing.
2. **Enables Deep Analytics**: Having fields like `RFNDAMT` (Refund Amount), `BNKCODE` (Bank Code), and `PEMNDG` (Category) in the database enables querying bank-wise rejection rates, HNI vs. Retail allotment success ratios, and refund tracking.
3. **Audit Trail for Dispute Resolution**: Buyers and sellers can verify exact transaction records and bank reference numbers (`RFNDNO`) directly from the database.
