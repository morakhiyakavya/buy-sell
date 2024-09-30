import re
from bs4 import BeautifulSoup

# Sample HTML content (replace it with your actual content)
html_content = '''
<div class="MuiTableContainer-root css-kge0eu">
    <table class="MuiTable-root css-1owb465">
        <tbody class="MuiTableBody-root css-1xnox0e">
            <tr class="MuiTableRow-root css-15mmw0j">
                <td class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                    <div
                        class="MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation1 MuiCard-root css-1c4y56n">
                        <div class="MuiCardContent-root css-1qw96cp">
                            <div class="css-j7qwjs">
                                <div class="MuiGrid-root MuiGrid-container css-yrcxbo">
                                    <div class="MuiGrid-root css-1kgy3g2" style="justify-content: right;">
                                        <div
                                            class="MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorError MuiChip-filledError css-1oacwxg">
                                            <span class="MuiChip-label MuiChip-labelSmall css-tavflp">Not
                                                Allotted</span></div>
                                    </div>
                                </div>
                                <table class="MuiTable-root css-1owb465">
                                    <tbody class="MuiTableBody-root css-1xnox0e">
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Application Number:
                                                </a><br><b>MB00000016379727</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Category: </a><br><b>Shareholder</b></td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Name: </a><br><b>MASTER. KAVYA SHRENIKBHAI
                                                    SHAH</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                            </td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">DP ID Client ID: </a><br><b>12041XXXXXX77520</b>
                                            </td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">PAN: </a><br><b>XXXXXX188F</b></td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Applied: </a><br><b>2782</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Allotted: </a><br><b>0</b></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
            <tr class="MuiTableRow-root css-15mmw0j">
                <td class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                    <div
                        class="MuiPaper-root MuiPaper-elevation MuiPaper-rounded MuiPaper-elevation1 MuiCard-root css-1c4y56n">
                        <div class="MuiCardContent-root css-1qw96cp">
                            <div class="css-j7qwjs">
                                <div class="MuiGrid-root MuiGrid-container css-yrcxbo">
                                    <div class="MuiGrid-root css-1kgy3g2" style="justify-content: right;">
                                        <div
                                            class="MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorError MuiChip-filledError css-1oacwxg">
                                            <span class="MuiChip-label MuiChip-labelSmall css-tavflp">Not
                                                Allotted</span></div>
                                    </div>
                                </div>
                                <table class="MuiTable-root css-1owb465">
                                    <tbody class="MuiTableBody-root css-1xnox0e">
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Application Number:
                                                </a><br><b>N000000016602766</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Category: </a><br><b>Non Institutional</b></td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Name: </a><br><b>MASTER. KAVYA SHRENIKBHAI
                                                    SHAH</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                            </td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">DP ID Client ID: </a><br><b>12041XXXXXX77520</b>
                                            </td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">PAN: </a><br><b>XXXXXX188F</b></td>
                                        </tr>
                                        <tr class="MuiTableRow-root css-15mmw0j">
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Applied: </a><br><b>14338</b></td>
                                            <td
                                                class="MuiTableCell-root MuiTableCell-body MuiTableCell-sizeMedium css-qkqlx2">
                                                <a style="color: grey;">Allotted: </a><br><b>0</b></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</div>
'''

# Parse the HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Initialize result_data dictionary
result_data = {}

# Find all relevant divs
divs = soup.find_all('div', class_='MuiCardContent-root css-1qw96cp')
print(f"Found {len(divs)} divs with class 'MuiCardContent-root css-1qw96cp'")

# Define the order of keys
keys = [
    'application_number',
    'category',
    'name',
    'dp_id_client_id',
    'pan',
    'applied',
    'allotted'
]

# Iterate over each div and extract data
for i, div in enumerate(divs, start=1):
    print(f"\nProcessing div {i}")
    
    # Extract bold text from the div
    bold_texts = div.find_all('b')
    print(f"Found {len(bold_texts)} bold elements in div {i}")
    
    # Initialize a dictionary to hold data for the current div
    current_data = {}
    
    # Assign bold text to keys in the defined order
    for index, bold in enumerate(bold_texts):
        text = bold.get_text(strip=True)
        if index < len(keys):
            key = keys[index]
            current_data[f"{key}_{i}"] = re.sub(r'\s+', ' ', text.strip())
            print(f"Added to current_data: {key}_{i}: {text}")
    
    # Merge current data into result_data
    result_data.update(current_data)

# Print the result_data dictionary
print("\nFinal result_data:", result_data)