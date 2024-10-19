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

# Map education levels to numeric values for comparison
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

# Filter matches for a girl using the flexibility slider
def filter_matches_for_girl_updated(girl, boys_profiles, flexibility):
    girl_age = int(girl['Age']) if pd.notna(girl['Age']) else None
    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(0).astype(int)

    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    # Filter based on flexibility
    matches = boys_profiles[
        ((boys_profiles['Hight/CM'] > girl['Hight/CM'] - flexibility) | pd.isnull(girl['Hight/CM'])) &
        ((boys_profiles['Marital Status'] == girl['Marital Status']) | pd.isnull(girl['Marital Status'])) &
        ((boys_profiles['Effective_boys_Age'] >= girl_age) & (boys_profiles['Effective_boys_Age'] <= girl_age + 5)) &
        ((boys_profiles['Denomination'] == girl['Denomination']) | pd.isnull(girl['Denomination'])) &
        ((boys_profiles['City'] == girl['City']) | pd.isnull(girl['City'])) &
        (boys_profiles['Education_Level'] >= girl_education_level - flexibility)
    ]

    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Filter matches for a boy using the flexibility slider
def filter_matches_for_boy_updated(boy, girls_profiles, flexibility):
    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    # Filter based on flexibility
    matches = girls_profiles[
        ((girls_profiles['Hight/CM'] < boy['Hight/CM'] + flexibility) | pd.isnull(boy['Hight/CM'])) &
        ((girls_profiles['Marital Status'] == boy['Marital Status']) | pd.isnull(boy['Marital Status'])) &
        ((girls_profiles['Age'] < boy['Age']) | pd.isnull(boy['Age'])) &
        ((girls_profiles['Denomination'] == boy['Denomination']) | pd.isnull(boy['Denomination'])) &
        ((girls_profiles['City'] == boy['City']) | pd.isnull(boy['City'])) &
        (girls_profiles['Education_Level'] >= boy_education_level - flexibility)
    ]

    return matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Save matches to a CSV file
def save_matches_to_csv(selected_profile, matches, output_directory):
    def sanitize_filename(name):
        if isinstance(name, str):
            return name.replace(" ", "_").replace(".", "_").replace("/", "_").replace("\\", "_")
        return "unknown"

    sanitized_name = sanitize_filename(selected_profile['Name'])
    file_path = os.path.join(output_directory, f"matches_for_{sanitized_name}.csv")
    matches.to_csv(file_path, index=False)

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
                st.error(f"The following required columns are missing: {', '.join(missing_columns)}")
                return

            profiles = data[required_columns]
            profiles['JIOID'] = profiles['JIOID'].astype(str)
            
            girls_profiles, boys_profiles = split_profiles_updated(profiles)
            
            # Flexibility slider
            flexibility = st.slider("Set Flexibility for Matching Criteria", 0, 10, 0)
            
            # Create dropdown with JIOID and Name for selection
            girl_options = [f"{row['JIOID']} - {row['Name']}" for idx, row in girls_profiles.iterrows()]
            boy_options = [f"{row['JIOID']} - {row['Name']}" for idx, row in boys_profiles.iterrows()]

            # Dropdowns for selecting profiles
            selected_girl = st.selectbox("Select a girl's profile to match:", girl_options)
            selected_boy = st.selectbox("Select a boy's profile to match:", boy_options)

            if st.button("Find Matches"):
                # Extract JIOID from selected profile strings
                selected_girl_jioid = selected_girl.split(" - ")[0]
                selected_boy_jioid = selected_boy.split(" - ")[0]

                if selected_girl_jioid in girls_profiles['JIOID'].values:
                    selected_profile = girls_profiles[girls_profiles['JIOID'] == selected_girl_jioid].iloc[0]
                    matches = filter_matches_for_girl_updated(selected_profile, boys_profiles, flexibility)
                elif selected_boy_jioid in boys_profiles['JIOID'].values:
                    selected_profile = boys_profiles[boys_profiles['JIOID'] == selected_boy_jioid].iloc[0]
                    matches = filter_matches_for_boy_updated(selected_profile, girls_profiles, flexibility)
                else:
                    st.error("Invalid profile selection.")
                    return

                if not matches.empty:
                    st.write(matches)
                    output_directory = st.text_input("Enter the directory to save matches CSV:")
                    if output_directory:
                        save_matches_to_csv(selected_profile, matches, output_directory)
                        st.success(f"Matches saved to {output_directory}")
                else:
                    st.warning("No matches found.")
        except Exception as e:
            st.error(f"Error loading or processing data: {str(e)}")

if __name__ == "__main__":
    main()
