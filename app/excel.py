import pandas as pd

# Function to extract specific column data from an Excel file

    
def process_excel_data(filepath, pan_Column, start_Row, end_Row=None):
    """
    Process the data from an Excel file and extract a specific column.

    Args:
        pan_Column (str or int): The index or label of the column to extract.
        start_Row (int): The starting row index.
        end_Row (int, optional): The ending row index. If not provided, all rows starting from start_Row will be considered.

    Returns:
        list: A list of values from the specified column.

    Raises:
        ValueError: If the pan_Column is out of range.

    """
    df = pd.read_excel(filepath)
    column_data = column_det(pan_Column, df)
    
    if end_Row:
        username = column_data[start_Row:end_Row].tolist()
    else:
        username = column_data[start_Row:].tolist()
    
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
    identifier_pan_Column = excel_col_to_index(identifier_column_letter)
    identifier_column_name = df.columns[identifier_pan_Column]

    for identifier, updates in updates_dict.items():
        if identifier in df[identifier_column_name].values:
            row_index = df.index[df[identifier_column_name] == identifier].tolist()[0]
            starting_col_index = identifier_pan_Column + 1  # Start writing to the next column
            for update in updates.values():
                if starting_col_index >= len(df.columns):
                    # Add a new column if we're beyond the existing ones
                    new_col_name = f"NewCol_{starting_col_index}"
                    df[new_col_name] = pd.NA  # Initialize new column
                column_name = df.columns[starting_col_index]
                df.at[row_index, column_name] = update
                starting_col_index += 1
        else:
            print(f"Identifier '{identifier}' not found in column '{identifier_column_name}'.")

    return df


