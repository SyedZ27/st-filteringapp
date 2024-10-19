import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Load the Excel file and handle duplicate columns
def load_data(file_path):
    """Loads data from an Excel file into a pandas DataFrame and handles duplicate columns."""
    data = pd.read_excel(file_path)
    
    # Check for duplicate column names
    if data.columns.duplicated().any():
        st.warning("Duplicate columns found. Renaming them to ensure uniqueness.")
        data.columns = pd.io.parsers.ParserBase({'names': data.columns})._maybe_dedup_names(data.columns)
    
    return data

# Function to calculate age from date of birth
def calculate_age(birthdate):
    """Calculates age from the given birthdate."""
    today = datetime.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

# Convert height to cm
def convert_height_to_cm(height_str):
    """Converts height given in different string formats to centimeters."""
    if pd.isnull(height_str):
        return None

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

# Clean and preprocess data with updated column names
def preprocess_data_updated(data):
    """Cleans and preprocesses the raw data with updated column names."""
    if 'Date Of Birth' in data.columns:
        data['Date Of Birth'] = pd.to_datetime(data['Date Of Birth'], errors='coerce', dayfirst=True)
        data['Age'] = data['Date Of Birth'].apply(lambda x: calculate_age(x) if pd.notnull(x) else None)
    else:
        st.warning("'Date Of Birth' column not found. Age calculation will be skipped.")
        data['Age'] = None
    
    if 'gender' in data.columns:
        data['gender'] = data['gender'].str.lower().str.strip()
    
    return data

# Split profiles into girls and boys using updated gender column
def split_profiles_updated(profiles):
    profiles['gender'] = profiles['gender'].str.lower().str.strip()
    girls_profiles = profiles[profiles['gender'] == 'female'].copy()
    boys_profiles = profiles[profiles['gender'] == 'male'].copy()

    girls_profiles.loc[:, 'Hight/CM'] = girls_profiles['Hight/FT'].apply(convert_height_to_cm)
    boys_profiles.loc[:, 'Hight/CM'] = boys_profiles['Hight/FT'].apply(convert_height_to_cm)

    return girls_profiles, boys_profiles

# Map education levels to numeric values
def map_education_level(education):
    education_hierarchy = {
        'highschool': 1,
        'bachelors': 2,
        'medicine': 3,
        'masters': 4,
        'phd': 5
    }
    if isinstance(education, str):
        return education_hierarchy.get(education.lower(), 0)
    return 0

# Filter matches for a girl using 'Education_Standardized'
def filter_matches_for_girl_updated(girl, boys_profiles):
    girl_age = girl['Age'] if pd.notna(girl['Age']) else girl['Age']
    girl_age = int(girl_age)

    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(boys_profiles['Age']).fillna(0).astype(int)
    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    matches = boys_profiles[
        (boys_profiles['Hight/CM'] > girl['Hight/CM']) &
        (boys_profiles['Marital Status'] == girl['Marital Status']) &
        (boys_profiles['Effective_boys_Age'] >= girl_age) &
        (boys_profiles['Effective_boys_Age'] <= girl_age + 5) &
        (boys_profiles['Denomination'] == girl['Denomination']) &
        (boys_profiles['City'] == girl['City']) &
        (boys_profiles['Education_Level'] == girl_education_level)
    ]

    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Denomination', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Filter matches for a boy using 'Education_Standardized'
def filter_matches_for_boy_updated(boy, girls_profiles):
    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    matches = girls_profiles[
        (girls_profiles['Hight/CM'] < boy['Hight/CM']) &
        (girls_profiles['Marital Status'] == boy['Marital Status']) &
        (girls_profiles['Age'] < boy['Age']) &
        (girls_profiles['Denomination'] == boy['Denomination']) &
        (girls_profiles['City'] == boy['City']) &
        (girls_profiles['Education_Level'] == boy_education_level)
    ]

    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Denomination', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Save matches to a CSV file
def save_matches_to_csv(selected_profile, matches, output_directory):
    def sanitize_filename(name):
        if isinstance(name, str):
            return name.replace(" ", "_").replace(".", "_").replace("/", "_").replace("\\", "_")
        return "unknown"

    sanitized_name = sanitize_filename(selected_profile['Name'])
    file_path = os.path.join(output_directory, f"matches_for_{sanitized_name}.csv")
    matches.to_csv(file_path, index=False)

# Main function to run the profile matching process in Streamlit
def main():
    st.title("Profile Matching Application")
    
    file_path = st.file_uploader("Upload an Excel file", type=["xlsx"])
    
    if file_path is not None:
        try:
            data = load_data(file_path)
            
            st.write("Columns in the uploaded file:", data.columns.tolist())
            
            data = preprocess_data_updated(data)
            
            required_columns = ['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/FT', 'gender', 
                                'City', 'Age', 'Education_Standardized', 'Salary-PA', 'Denomination', 'Occupation', 
                                'joined', 'expire_date', 'Mobile', 'Date Of Birth']
            
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                st.error(f"The following required columns are missing: {', '.join(missing_columns)}")
                st.error("Please ensure your Excel file contains all required columns.")
                return
            
            profiles = data[required_columns]
            profiles['JIOID'] = profiles['JIOID'].astype(str)
            
            girls_profiles, boys_profiles = split_profiles_updated(profiles)
            
            input_id = st.text_input("Enter the JIOID of the profile to match:")

            if st.button("Find Matches"):
                if input_id in girls_profiles['JIOID'].values:
                    selected_profile = girls_profiles[girls_profiles['JIOID'] == input_id].iloc[0]
                    matches = filter_matches_for_girl_updated(selected_profile, boys_profiles)
                elif input_id in boys_profiles['JIOID'].values:
                    selected_profile = boys_profiles[boys_profiles['JIOID'] == input_id].iloc[0]
                    matches = filter_matches_for_boy_updated(selected_profile, girls_profiles)
                else:
                    st.error(f"No profile found with JIOID {input_id}.")
                    return

                st.write("Matched profiles:")
                st.write(matches)

                if st.button("Save Matches"):
                    output_directory = "FINAL"
                    if not os.path.exists(output_directory):
                        os.makedirs(output_directory)
                    save_matches_to_csv(selected_profile, matches, output_directory)
                    st.success(f"Matches saved to {output_directory}.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
