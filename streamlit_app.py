import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Load the Excel file
def load_data(file_path):
    """Loads data from an Excel file into a pandas DataFrame."""
    return pd.read_excel(file_path)

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

    # Mixed formats like "5ft 5in - 165"
    if 'ft' in height_str and '-' in height_str:
        try:
            feet_inches = height_str.split('-')[0].strip()
            feet, inches = feet_inches.split('ft ')
            inches = inches.split('in')[0].strip()
            return int(feet.strip()) * 30.48 + int(inches) * 2.54
        except ValueError:
            return None

    # Check if the height is already in centimeters (e.g., "165cm")
    if 'cm' in height_str:
        try:
            return int(height_str.split('cm')[0].strip())
        except ValueError:
            return None

    # Handle feet and inches only (e.g., "5ft 5in")
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
    
    # Handle gender (previously Bride/Bridegroom)
    if 'gender' in data.columns:
        data['gender'] = data['gender'].str.lower().str.strip()
    
    return data

# Split profiles into girls and boys using updated gender column
def split_profiles_updated(profiles):
    profiles['gender'] = profiles['gender'].str.lower().str.strip()
    girls_profiles = profiles[profiles['gender'] == 'female'].copy()
    boys_profiles = profiles[profiles['gender'] == 'male'].copy()

    # Apply height conversion using 'Hight/FT'
    girls_profiles.loc[:, 'Hight/CM'] = girls_profiles['Hight/FT'].apply(convert_height_to_cm)
    boys_profiles.loc[:, 'Hight/CM'] = boys_profiles['Hight/FT'].apply(convert_height_to_cm)

    return girls_profiles, boys_profiles

# Define a function to map education levels to numeric values
def map_education_level(education):
    """Maps education levels to numeric values for comparison."""
    education_hierarchy = {
        'highschool': 1,
        'bachelors': 2,
        'medicine': 3,
        'masters': 4,
        'phd': 5
    }
    if isinstance(education, str):
        return education_hierarchy.get(education.lower(), 0)  # Return 0 if the education level is not found
    return 0  # Default for non-string types

# Flexibility-based matching for girls
def filter_matches_with_flexibility(girl, boys_profiles, flexibility=2):
    """Filters boys profiles based on the girl's criteria with flexibility for unmatched conditions."""
    girl_age = girl['Age'] if pd.notna(girl['Age']) else girl['Age']
    girl_age = int(girl_age)
    
    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(boys_profiles['Age']).fillna(0).astype(int)

    # Use standardized education column
    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    # Flexibility logic: keep track of how many conditions are violated
    def condition_check(row):
        conditions_met = 0
        
        # Conditions
        if row['Hight/CM'] > girl['Hight/CM']:
            conditions_met += 1
        if row['Marital Status'] == girl['Marital Status']:
            conditions_met += 1
        if girl_age <= row['Effective_boys_Age'] <= girl_age + 5:
            conditions_met += 1
        if row['Denomination'] == girl['Denomination']:
            conditions_met += 1
        if row['City'] == girl['City']:
            conditions_met += 1
        if row['Education_Level'] == girl_education_level:
            conditions_met += 1

        # Return True if the number of failed conditions is within flexibility allowance
        return conditions_met >= (6 - flexibility)

    # Filter profiles based on the flexible condition-checking logic
    matches = boys_profiles[boys_profiles.apply(condition_check, axis=1)]

    # Return relevant columns
    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Flexibility-based matching for boys
def filter_matches_for_boy_with_flexibility(boy, girls_profiles, flexibility=2):
    """Filters girls profiles based on the boy's criteria with flexibility for unmatched conditions."""
    boy_age = boy['Age'] if pd.notna(boy['Age']) else boy['Age']
    boy_age = int(boy_age)
    
    girls_profiles['Effective_girls_Age'] = girls_profiles['Age'].fillna(girls_profiles['Age']).fillna(0).astype(int)

    # Use standardized education column
    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    # Flexibility logic: keep track of how many conditions are violated
    def condition_check(row):
        conditions_met = 0
        
        # Conditions
        if row['Hight/CM'] < boy['Hight/CM']:
            conditions_met += 1
        if row['Marital Status'] == boy['Marital Status']:
            conditions_met += 1
        if row['Effective_girls_Age'] < boy_age:
            conditions_met += 1
        if row['Denomination'] == boy['Denomination']:
            conditions_met += 1
        if row['City'] == boy['City']:
            conditions_met += 1
        if row['Education_Level'] == boy_education_level:
            conditions_met += 1

        # Return True if the number of failed conditions is within flexibility allowance
        return conditions_met >= (6 - flexibility)

    # Filter profiles based on the flexible condition-checking logic
    matches = girls_profiles[girls_profiles.apply(condition_check, axis=1)]

    # Return relevant columns
    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Save matches to a CSV file
def save_matches_to_csv(selected_profile, matches, output_directory):
    """Saves the matched profiles to a CSV file."""
    def sanitize_filename(name):
        """Sanitizes the name for use in a file name.""" 
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
            
            # Preprocess data
            data = preprocess_data_updated(data)
            
            # Define required columns
            required_columns = ['JIOID', 'Name', 'Cast', 'Marital Status', 'Hight/FT', 'gender', 
                                'City', 'Age', 'Education_Standardized', 'Salary-PA', 'Denomination', 'Occupation', 
                                'joined', 'expire_date', 'Mobile', 'Date Of Birth']
            
            # Check for missing columns
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                st.error(f"The following required columns are missing: {', '.join(missing_columns)}")
                return
            
            girls_profiles, boys_profiles = split_profiles_updated(data)
            
            st.write(f"Loaded {len(girls_profiles)} girl profiles and {len(boys_profiles)} boy profiles.")
            
            profile_type = st.radio("Select profile type to match", ["Girl", "Boy"])
            
            if profile_type == "Girl":
                selected_girl_index = st.selectbox("Select a girl's profile to match", range(len(girls_profiles)))
                selected_girl = girls_profiles.iloc[selected_girl_index]
                flexibility = st.slider("Set flexibility level for matching", min_value=0, max_value=5, value=2)
                matches = filter_matches_with_flexibility(selected_girl, boys_profiles, flexibility)
                st.write(f"Found {len(matches)} matches for {selected_girl['Name']}")
                st.write(matches)
                
                output_directory = st.text_input("Enter the output directory to save matches")
                if st.button("Save matches to CSV") and output_directory:
                    save_matches_to_csv(selected_girl, matches, output_directory)
                    st.success("Matches saved successfully.")
            
            elif profile_type == "Boy":
                selected_boy_index = st.selectbox("Select a boy's profile to match", range(len(boys_profiles)))
                selected_boy = boys_profiles.iloc[selected_boy_index]
                flexibility = st.slider("Set flexibility level for matching", min_value=0, max_value=5, value=2)
                matches = filter_matches_for_boy_with_flexibility(selected_boy, girls_profiles, flexibility)
                st.write(f"Found {len(matches)} matches for {selected_boy['Name']}")
                st.write(matches)
                
                output_directory = st.text_input("Enter the output directory to save matches")
                if st.button("Save matches to CSV") and output_directory:
                    save_matches_to_csv(selected_boy, matches, output_directory)
                    st.success("Matches saved successfully.")
        
        except Exception as e:
            st.error(f"Error loading the file: {e}")

if __name__ == "__main__":
    main()
