import re

def clean_and_split(text):
    # Remove timestamps and sender labels like [07-05-2025 23:48] Papa:
    text = re.sub(r'\[\d{2}-\d{2}-\d{4} \d{2}:\d{2}\] Papa: ?', '', text)
    text = re.sub(r'[\u200c\u200b]+', '', text)  # Remove zero-width characters
    return [line.strip() for line in text.splitlines() if line.strip()]

def extract_pans(lines):
    pan_pattern = re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', re.IGNORECASE)
    result = []
    for i, line in enumerate(lines):
        matches = pan_pattern.findall(line)
        for pan in matches:
            result.append((i, pan.upper()))
    return result

import spacy
nlp = spacy.load("en_core_web_sm")

def find_name(line, pan, fallback_lines):
    # Try to extract name directly from line (before PAN)
    before_pan = line.split(pan)[0].strip()
    if before_pan and len(before_pan) > 2:
        return before_pan.strip(":.").title()

    # Else, look nearby
    for nearby in fallback_lines:
        doc = nlp(nearby)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.title()

    return "Unknown"


import pandas as pd

def build_table(lines):
    pan_lines = extract_pans(lines)
    rows = []

    for idx, pan in pan_lines:
        name_line = lines[idx]
        nearby = lines[max(0, idx-2):idx] + lines[idx+1:idx+3]
        name = find_name(name_line, pan, nearby)
        rows.append({"Name": name, "PAN": pan})

    return pd.DataFrame(rows)
# Example usage
if __name__ == "__main__":
    input_text = r"""
[07-05-2025 23:48] Papa: SUNITA...BOYPB0474G
HANISH....CIFPB6309C
[07-05-2025 23:49] Papa: Ok
AKIPB2874M... RAJENDRA
&
RAMESH ...BOYPB0674N
[07-05-2025 23:50] Papa: KAUTILYA GELOT
CSVPG1491A
[07-05-2025 23:50] Papa: Sriger sub to 31000

Name : Tapasya shah
Pan no : RRRPS6808D
Name : Kriya shah
Pan no : KRTPS4143E
[07-05-2025 23:51] Papa: Rushabh Doshi
Cpapd6250C

Rushabh Doshi Huf
AAZHR6311Q
"""

    cleaned_lines = clean_and_split(input_text)
    df = build_table(cleaned_lines)
    print(df.to_markdown(index=False))

# import re
# import pandas as pd

# def extract_name_pan(text):
#     pan_regex = re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', re.IGNORECASE)
#     name_pan_pairs = []

#     lines = text.strip().splitlines()
#     cleaned_lines = [line.strip() for line in lines if line.strip()]

#     i = 0
#     while i < len(cleaned_lines):
#         line = cleaned_lines[i]

#         # Skip system lines
#         if line.startswith("[") or line.startswith("\\["):
#             i += 1
#             continue

#         # Extract PAN in the current line
#         pan_match = pan_regex.search(line)
#         if pan_match:
#             pan = pan_match.group(1).upper()
#             name = None

#             # 1. Try to extract name from same line (either before or after the PAN)
#             before = line[:pan_match.start()].strip(" .:-").strip()
#             after = line[pan_match.end():].strip(" .:-").strip()

#             if before and len(before) > 2:
#                 name = before
#             elif after and len(after) > 2:
#                 name = after
#             else:
#                 # 2. Look above and below
#                 prev_line = cleaned_lines[i-1] if i > 0 else ""
#                 next_line = cleaned_lines[i+1] if i+1 < len(cleaned_lines) else ""

#                 # Handle "Name : <name>" structure
#                 for check_line in [prev_line, next_line]:
#                     match = re.search(r'Name\s*:\s*(.+)', check_line, re.IGNORECASE)
#                     if match:
#                         name = match.group(1).strip()
#                         break

#                 # Otherwise just use previous line if it's not a PAN line
#                 if not name:
#                     if prev_line and not pan_regex.search(prev_line) and not prev_line.startswith("["):
#                         name = prev_line.strip(" .:-")

#             if not name or len(name) < 2:
#                 name = "Unknown"

#             name_pan_pairs.append((name, pan))

#         i += 1

#     df = pd.DataFrame(name_pan_pairs, columns=["Name", "PAN"])
#     return df

# # Example usage
# if __name__ == "__main__":
#     input_text = r"""
# [07-05-2025 23:48] Papa: SUNITA...BOYPB0474G
# HANISH....CIFPB6309C
# [07-05-2025 23:49] Papa: Ok
# AKIPB2874M... RAJENDRA
# &
# RAMESH ...BOYPB0674N
# [07-05-2025 23:50] Papa: KAUTILYA GELOT
# CSVPG1491A
# [07-05-2025 23:50] Papa: Sriger sub to 31000
# Name : Tapasya shah
# Pan no : RRRPS6808D

# Name : Kriya shah
# Pan no : KRTPS4143E
# [07-05-2025 23:51] Papa: Rushabh Doshi
# Cpapd6250C

# Rushabh Doshi Huf
# AAZHR6311Q
# """

#     df = extract_name_pan(input_text)
#     print(df.to_markdown(index=False))
