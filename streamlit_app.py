import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Load the Excel file
def load_data(file_path):
    """Loads data from an Excel file into a pandas DataFrame."""
    data = pd.read_excel(file_path)
    st.write("Column Names in the Uploaded File:", data.columns)  # Debugging step to show column names
    return data

# Function to calculate age from date of birth
def calculate_age(birthdate):
    """Calculates age from the given birthdate."""
    today = datetime.now()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

# Convert height to cm
def convert_height_to_cm(height_str):
    """Converts height given in different string formats to centimeters."""
    if pd.isnull(height_str):
        return None

    if isinstance(height_str, (int, float)):
        return height_str

    height_str = str(height_str).lower()

    if 'ft' in height_str and '-' in height_str:
        try:
            feet_inches = height_str.split('-')[0].strip()
            feet, inches = feet_inches.split('ft ')
            inches = inches.split('in')[0].strip()
            return int(feet.strip()) * 30.48 + int(inches) * 2.54
        except ValueError:
            return None

    if 'cm' in height_str:
        try:
            return int(height_str.split('cm')[0].strip())
        except ValueError:
            return None

    if 'ft' in height_str:
        try:
            feet, inches = height_str.split('ft ')
            inches = inches.split('in')[0].strip()
            return int(feet.strip()) * 30.48 + int(inches) * 2.54
        except ValueError:
            return None

    return None

# Function to clean and standardize salary values (convert "5LPA" to 5.0)
def clean_salary(salary_str):
    """Cleans and standardizes salary values from strings like '5LPA'."""
    if pd.isnull(salary_str):
        return None
    
    salary_str = str(salary_str).replace(" ", "").lower()  # Remove spaces and convert to lowercase
    
    try:
        if 'lpa' in salary_str:
            salary_value = float(salary_str.replace("lpa", "").strip())  # Remove 'LPA' and convert to float
            return salary_value
    except ValueError:
        return None
    
    return None

# Clean and preprocess data with updated column names
def preprocess_data_updated(data):
    """Cleans and preprocesses the raw data with updated column names."""
    # Strip leading and trailing spaces from column names
    data.columns = data.columns.str.strip()

    # Handling 'Date Of Birth' for age calculation
    if 'Date Of Birth' in data.columns:
        data['Date Of Birth'] = pd.to_datetime(data['Date Of Birth'], errors='coerce', dayfirst=True)
        data['Age'] = data.apply(lambda row: calculate_age(row['Date Of Birth']) if pd.notnull(row['Date Of Birth']) else row['Age'], axis=1)
    else:
        st.warning("'Date Of Birth' column not found. Age calculation will be skipped.")
        data['Age'] = None

    # Standardize 'gender' column
    if 'gender' in data.columns:
        data['gender'] = data['gender'].str.lower().str.strip()

    # Handle potential spaces in 'Salary-PA_Standardized' column name
    salary_col = next((col for col in data.columns if col.strip().lower() == 'salary-pa_standardized'.lower()), None)
    if salary_col is not None:
        data[salary_col] = data[salary_col].str.replace(' ', '').str.lower()

    return data


# Split profiles into girls and boys using updated gender column
def split_profiles_updated(profiles):
    profiles['gender'] = profiles['gender'].str.lower().str.strip()
    girls_profiles = profiles[profiles['gender'] == 'female'].copy()
    boys_profiles = profiles[profiles['gender'] == 'male'].copy()

    girls_profiles.loc[:, 'Hight/CM'] = girls_profiles['Hight/FT'].apply(convert_height_to_cm)
    boys_profiles.loc[:, 'Hight/CM'] = boys_profiles['Hight/FT'].apply(convert_height_to_cm)

    return girls_profiles, boys_profiles

# Map education levels to numeric values for comparison
def map_education_level(education):
    education_hierarchy = {
        'secondary education': 0,
        'diploma': 1,
        'bachelors': 2,
        'masters': 3,
        'law': 4,
        'doctorate': 5,
        'phd': 6,
        'doctor': 7
    }
    if isinstance(education, str):
        return education_hierarchy.get(education.lower().strip(), 0)  # Convert to lowercase
    return 0

def filter_matches_for_boy_updated(boy, girls_profiles):
    boy_age = int(boy['Age']) if pd.notna(boy['Age']) else None
    girls_profiles['Effective_girls_Age'] = girls_profiles['Age'].fillna(0).astype(int)

    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    # Clean salary values for comparison
    boy_salary = clean_salary(boy['Salary-PA_Standardized'])
    
    matches = girls_profiles[
        ((girls_profiles['Hight/CM'] < boy['Hight/CM']) | pd.isnull(boy['Hight/CM'])) &
        ((girls_profiles['Marital Status'] == boy['Marital Status']) | pd.isnull(boy['Marital Status'])) &
        ((girls_profiles['Effective_girls_Age'] >= boy_age - 5) & (girls_profiles['Effective_girls_Age'] <= boy_age)) &
        (girls_profiles['Education_Level'] <= boy_education_level) &
        ((girls_profiles['Salary-PA_Standardized'] < boy_salary) | pd.isnull(girls_profiles['Salary-PA_Standardized']))  # Salary condition
    ]

    # Prioritize same city matches
    same_city_matches = matches[matches['City'] == boy['City']]
    different_city_matches = matches[matches['City'] != boy['City']]

    prioritized_matches = pd.concat([same_city_matches, different_city_matches])

    return prioritized_matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA_Standardized', 'Occupation', 'joined', 'expire_date', 'Mobile']]

def filter_matches_for_girl_updated(girl, boys_profiles):
    girl_age = int(girl['Age']) if pd.notna(girl['Age']) else None
    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(0).astype(int)

    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    # Clean salary values for comparison
    girl_salary = clean_salary(girl['Salary-PA_Standardized'])
    
    matches = boys_profiles[
        ((boys_profiles['Hight/CM'] > girl['Hight/CM']) | pd.isnull(girl['Hight/CM'])) &
        ((boys_profiles['Marital Status'] == girl['Marital Status']) | pd.isnull(girl['Marital Status'])) &
        ((boys_profiles['Effective_boys_Age'] >= girl_age + 1) & (boys_profiles['Effective_boys_Age'] <= girl_age + 5)) &
        (boys_profiles['Education_Level'] >= girl_education_level) &
        ((boys_profiles['Salary-PA_Standardized'] > girl_salary) | pd.isnull(boys_profiles['Salary-PA_Standardized']))  # Salary condition
    ]

    # Prioritize same city matches
    same_city_matches = matches[matches['City'] == girl['City']]
    different_city_matches = matches[matches['City'] != girl['City']]

    prioritized_matches = pd.concat([same_city_matches, different_city_matches])

    return prioritized_matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA_Standardized', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Main function remains the same


# Main function
def main():
    st.title("Profile Matching Application")

    file_path = st.file_uploader("Upload an Excel file", type=["xlsx"])

    if file_path is not None:
        try:
            data = load_data(file_path)
            data = preprocess_data_updated(data)

            required_columns = ['JIOID', 'Name', 'Cast', 'Marital Status', 'Hight/FT', 'gender', 
                                'City', 'Age', 'Education_Standardized', 'Salary-PA', 'Denomination', 'Occupation', 
                                'joined', 'expire_date', 'Mobile', 'Date Of Birth']

            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                st.warning(f"Missing columns in the uploaded file: {', '.join(missing_columns)}")
                return

            # Filter profiles based on gender
            girls_profiles, boys_profiles = split_profiles_updated(data)

            # Match profiles for boys
            matches_dict = {}
            for index, boy in boys_profiles.iterrows():
                matches = filter_matches_for_boy_updated(boy, girls_profiles)
                if not matches.empty:
                    matches_dict[boy['Name']] = matches

            # Match profiles for girls
            for index, girl in girls_profiles.iterrows():
                matches = filter_matches_for_girl_updated(girl, boys_profiles)
                if not matches.empty:
                    matches_dict[girl['Name']] = matches

            if matches_dict:
                for name, matches in matches_dict.items():
                    st.write(f"Matches for {name}:")
                    st.dataframe(matches)
            else:
                st.write("No matches found.")

        except Exception as e:
            st.error(f"An error occurred: {e}")

# Run the main function
if __name__ == "__main__":
    main()
