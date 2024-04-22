import pandas as pd
import re
import spacy

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")
# Function to extract specific column data from an Excel file

    
def process_excel_data(filepath, pan_Column, start_Row, end_Row=None):
    """
    Process the data from an Excel file and extract a specific column.

    Args:
        pan_Column (str or int): The index or label of the column to extract.
        start_Row (int): The starting row number in the Excel sheet (1-based index).
        end_Row (int, optional): The ending row number in the Excel sheet. If not provided, all rows starting from start_Row will be considered.

    Returns:
        list: A list of values from the specified column.

    Raises:
        ValueError: If the pan_Column is out of range.

    """
    df = pd.read_excel(filepath)
    column_data = column_det(pan_Column, df)
    
    # Adjust start_Row and end_Row to zero-based index
    if start_Row > 1:
        start_Row -= 2
    else:
        start_Row -= 1
    if end_Row:
        end_Row -= 2  # Adjust end_Row to zero-based index
        username = column_data[start_Row:end_Row].tolist()
    else:
        username = column_data[start_Row:].tolist()
    
    # print(f"Column data : {column_data[start_Row]} and end row : {column_data[end_Row]}")
    return username

def column_det(pan_Column, df):
    if isinstance(pan_Column, str):
        # Convert Excel column letter to zero-based index
        pan_Column = ord(pan_Column.upper()) - ord('A')
    
    if isinstance(pan_Column, int):
        if pan_Column < 0 or pan_Column >= len(df.columns):
            raise ValueError("Invalid column index")
        column_data = df.iloc[:, pan_Column]
    else:
        raise ValueError("Invalid column identifier")
    return column_data

def write_in_excel(file_path, results, pan_Column):
    """
    Writes data to an Excel file, updating existing rows based on a unique identifier (column_name)
    and appending new rows if the identifier does not exist. Dynamically adds new columns if
    they do not exist in the DataFrame.

    Args:
        file_path (str): Path to the Excel file where data will be written.
        df (pd.DataFrame): The DataFrame to update.
        results (dict): A dictionary containing the data to be written. The keys are identifiers
                        and the values are dictionaries representing the updates to be made.

    Returns:
        None
    """
    df = pd.read_excel(file_path)

    #For getting column name
    
    if isinstance(pan_Column, str):
        # Convert Excel column letter to zero-based index
        pan_Column = ord(pan_Column.upper()) - ord('A')
    
    column_name = df.columns[pan_Column]

    for identifier, updates in results.items():
        if identifier in df[column_name].values:
            # Update existing row(s)
            for column, value in updates.items():
                # Check if column exists, if not, add it
                if column not in df.columns:
                    df[column] = pd.NA  # Initialize new column with missing values
                df[column] = df[column].astype('object')
                df.loc[df[column_name] == identifier, column] = value
        else:
            # Append a new row if the identifier does not exist
            # Ensure all columns in updates exist or are added to the DataFrame
            for column in updates.keys():
                if column not in df.columns:
                    df[column] = pd.NA  # Initialize new column with missing values
            new_row = updates
            new_row[column_name] = identifier  # Ensure the unique identifier is included in the new row
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    # Save the updated DataFrame back to the Excel file
    df.to_excel(file_path, index=False)
    return df

def print_details(company, ipo, results):
    print("*-----------------------------------------------------*")

    print(f"Comapany {company} and IPO {ipo}")
    print("--------------------------------------------")
    for username, result in results.items():
    # print(f"{username}: {result}")
        print(f"{username}:")
        for key, value in result.items():
            print(f"\t{key}: {value}")
        print("-------------")

    print("*------------------------------------------------------------------*")
    return None

def get_column_data(file_path, column_identifier):
    df = pd.read_excel(file_path)
    if isinstance(column_identifier, int):  # Check if it's already an integer
        column_data = df.iloc[:, column_identifier]
    elif isinstance(column_identifier, str):  # Check if it's a string
        column_data = df[column_identifier]
    else:
        raise ValueError("Invalid column identifier")
    
    return column_data



# Define regular expressions for each data type
PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
DP_ID_PATTERN = re.compile(r'^\d{8,10}$')
# Updated pattern to capture more Indian name features and "HUF"
INDIAN_NAME_PATTERN = re.compile(r'(kumar|singh|devi|reddy|patel|das|rao|sharma|shah|huf)', re.IGNORECASE)

def check_confidence(column, pattern, threshold):
    # Convert column to uppercase if checking PAN pattern
    if pattern == PAN_PATTERN:
        column = column.str.upper()
    matches = column.apply(lambda x: bool(pattern.match(str(x))))
    confidence = matches.sum() / len(column)
    return confidence >= threshold, confidence

def check_name_confidence(column, threshold):
    name_counts = 0
    for text in column:
        doc = nlp(str(text))
        person_found = any(ent.label_ == "PERSON" for ent in doc.ents)
        heuristic_match = bool(INDIAN_NAME_PATTERN.search(str(text)))
        if person_found or heuristic_match:
            name_counts += 1
    confidence = name_counts / len(column)
    return confidence >= threshold, confidence

def classify_columns(df):
    results = {}
    thresholds = {'pan': 0.8, 'dp_id': 0.5, 'name': 0.5}

    for col in df.columns:
        is_pan, pan_confidence = check_confidence(df[col], PAN_PATTERN, thresholds['pan'])
        is_dp_id, dp_id_confidence = check_confidence(df[col], DP_ID_PATTERN, thresholds['dp_id'])
        is_name, name_confidence = check_name_confidence(df[col], thresholds['name'])
        
        confidences = {'pan': (is_pan, pan_confidence), 'dp_id': (is_dp_id, dp_id_confidence), 'name': (is_name, name_confidence)}
        assigned_label = max(confidences, key=lambda x: confidences[x][1] if confidences[x][0] else 0)
        
        # Ensure that no label is repeated and meets threshold criteria
        if confidences[assigned_label][0] and all(res[0] != assigned_label for res in results.values()):
            results[col] = (assigned_label, confidences[assigned_label][1])
        else:
            results[col] = ('unknown', 0)

    # Keep up to 3 best classified columns based on confidence
    if len(results) > 3:
        results = dict(sorted(results.items(), key=lambda item: item[1][1], reverse=True)[:3])

    return results

def process_excel(file_path):
    df = pd.read_excel(file_path, header=None)  # Assuming no header
    df.dropna(how='all', inplace=True)  # Drop all rows with all NaN values
    column_classifications = classify_columns(df)
    
    # Map new names and filter columns
    new_columns = {k: v[0] for k, v in column_classifications.items() if v[0] != 'unknown'}
    df = df[list(new_columns.keys())]
    df.rename(columns=new_columns, inplace=True)
    
    return df


