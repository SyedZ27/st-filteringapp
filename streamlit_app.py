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

# Clean and preprocess data with updated column names
def preprocess_data_updated(data):
    """Cleans and preprocesses the raw data with updated column names."""
    if 'Date Of Birth' in data.columns:
        data['Date Of Birth'] = pd.to_datetime(data['Date Of Birth'], errors='coerce', dayfirst=True)
        # If Date of Birth is NaT (missing), use the existing Age column
        data['Age'] = data.apply(lambda row: calculate_age(row['Date Of Birth']) if pd.notnull(row['Date Of Birth']) else row['Age'], axis=1)
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
        'Doctor': 3,
        'masters': 4,
        'phd': 5
    }
    if isinstance(education, str):
        return education_hierarchy.get(education.lower(), 0)
    return 0

# Filter matches for a boy with corrected age range and exact match conditions
def filter_matches_for_boy_updated(boy, girls_profiles):
    boy_age = int(boy['Age']) if pd.notna(boy['Age']) else None
    girls_profiles['Effective_girls_Age'] = girls_profiles['Age'].fillna(0).astype(int)

    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    # Apply the correct age condition (girls' age should be within 5 years younger)
    matches = girls_profiles[
        ((girls_profiles['Hight/CM'] < boy['Hight/CM']) | pd.isnull(boy['Hight/CM'])) &
        ((girls_profiles['Marital Status'] == boy['Marital Status']) | pd.isnull(boy['Marital Status'])) &
        ((girls_profiles['Effective_girls_Age'] >= boy_age - 5) & (girls_profiles['Effective_girls_Age'] <= boy_age)) &  # Match girls within boy's age range (up to 5 years younger)
        ((girls_profiles['Denomination'] == boy['Denomination']) | pd.isnull(boy['Denomination'])) &
        (girls_profiles['Education_Level'] >= boy_education_level)  # Exact match for education level
    ]

    # Split matches into same city and different city for prioritized output
    same_city_matches = matches[matches['City'] == boy['City']]
    different_city_matches = matches[matches['City'] != boy['City']]

    # Concatenate same city profiles first, followed by different city profiles
    prioritized_matches = pd.concat([same_city_matches, different_city_matches])

    return prioritized_matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Filter matches for a girl with corrected age conditions
def filter_matches_for_girl_updated(girl, boys_profiles):
    girl_age = int(girl['Age']) if pd.notna(girl['Age']) else None
    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(0).astype(int)

    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    # Apply the correct age condition (boys' age should be up to 5 years older)
    matches = boys_profiles[
        ((boys_profiles['Hight/CM'] > girl['Hight/CM']) | pd.isnull(girl['Hight/CM'])) &
        ((boys_profiles['Marital Status'] == girl['Marital Status']) | pd.isnull(girl['Marital Status'])) &
        ((boys_profiles['Effective_boys_Age'] >= girl_age + 1) & (boys_profiles['Effective_boys_Age'] <= girl_age + 5)) &  # Match boys within the girl's age range (up to 5 years older)
        ((boys_profiles['Denomination'] == girl['Denomination']) | pd.isnull(girl['Denomination'])) &
        (boys_profiles['Education_Level'] >= girl_education_level)  # Exact match for education level
    ]

    # Split matches into same city and different city for prioritized output
    same_city_matches = matches[matches['City'] == girl['City']]
    different_city_matches = matches[matches['City'] != girl['City']]

    # Concatenate same city profiles first, followed by different city profiles
    prioritized_matches = pd.concat([same_city_matches, different_city_matches])

    return prioritized_matches[['JIOID', 'Name', 'Denomination', 'Marital Status', 'Hight/CM', 'Age', 'City', 'Education_Standardized', 'Salary-PA', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Save matches to a CSV file
def save_matches_to_csv(selected_profile, matches, output_directory):
    def sanitize_filename(name):
        return "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip()

    sanitized_name = sanitize_filename(str(selected_profile['Name']))
    file_path = os.path.join(output_directory, f"matches_for_{sanitized_name}.csv")
    matches.to_csv(file_path, index=False)
    return file_path

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
            
            # Input field for JIOID
            selected_jioid = st.text_input("Enter JIOID of the user to match profiles:")

            if st.button("Find Matches"):
                if not selected_jioid:
                    st.error("Please enter a JIOID.")
                    return

                if selected_jioid in boys_profiles['JIOID'].values:
                    selected_profile = boys_profiles[boys_profiles['JIOID'] == selected_jioid].iloc[0]
                    matches = filter_matches_for_boy_updated(selected_profile, girls_profiles)

                    # Display the number of matches for the boy
                    num_matches = len(matches)
                    st.write(f"{num_matches} profiles matched for boy {selected_profile['Name']}:")
                    st.dataframe(matches)

                    output_directory = st.text_input("Enter the output directory for saving the matches:")
                    if st.button("Save Matches"):
                        if not output_directory:
                            st.error("Please enter a valid output directory.")
                        else:
                            file_path = save_matches_to_csv(selected_profile, matches, output_directory)
                            st.success(f"Matches saved to {file_path}")

                elif selected_jioid in girls_profiles['JIOID'].values:
                    selected_profile = girls_profiles[girls_profiles['JIOID'] == selected_jioid].iloc[0]
                    matches = filter_matches_for_girl_updated(selected_profile, boys_profiles)

                    # Display the number of matches for the girl
                    num_matches = len(matches)
                    st.write(f"{num_matches} profiles matched for girl {selected_profile['Name']}:")
                    st.dataframe(matches)

                    output_directory = st.text_input("Enter the output directory for saving the matches:")
                    if st.button("Save Matches"):
                        if not output_directory:
                            st.error("Please enter a valid output directory.")
                        else:
                            file_path = save_matches_to_csv(selected_profile, matches, output_directory)
                            st.success(f"Matches saved to {file_path}")

                else:
                    st.error("JIOID not found in the profiles.")
        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")

if __name__ == '__main__':
    main()
