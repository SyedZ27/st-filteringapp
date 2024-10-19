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

# Clean and preprocess data
def preprocess_data(data):
    """Cleans and preprocesses the raw data."""
    data['Date Of Birth'] = pd.to_datetime(data['Date Of Birth'], errors='coerce', dayfirst=True)
    data['RealAge'] = data['Date Of Birth'].apply(lambda x: calculate_age(x) if pd.notnull(x) else None)
    return data

# Split profiles into girls and boys
def split_profiles(profiles):
    profiles['Bride/Bridegroom'] = profiles['Bride/Bridegroom'].str.lower().str.strip()
    girls_profiles = profiles[profiles['Bride/Bridegroom'] == 'bride'].copy()
    boys_profiles = profiles[profiles['Bride/Bridegroom'] == 'bridegroom'].copy()

    # Apply height conversion
    girls_profiles.loc[:, 'Height_cm'] = girls_profiles['Hight/FT'].apply(convert_height_to_cm)
    boys_profiles.loc[:, 'Height_cm'] = boys_profiles['Hight/FT'].apply(convert_height_to_cm)

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

# Filter matches for a girl
def filter_matches_for_girl(girl, boys_profiles):
    """Filters boys profiles based on the given girl's criteria."""
    girl_age = girl['RealAge'] if pd.notna(girl['RealAge']) else girl['Age']
    girl_age = int(girl_age)

    # Create an effective age column for boys
    boys_profiles['Effective_boys_Age'] = boys_profiles['RealAge'].fillna(boys_profiles['Age']).fillna(0).astype(int)

    # Convert education levels to numeric values
    girl_education_level = map_education_level(girl['Education'])
    boys_profiles['Education_Level'] = boys_profiles['Education'].apply(map_education_level)

    # Filter boys based on matching criteria
    matches = boys_profiles[
        (boys_profiles['Height_cm'] > girl['Height_cm']) &
        (boys_profiles['Marital Status'] == girl['Marital Status']) &
        (boys_profiles['Effective_boys_Age'] >= girl_age) &
        (boys_profiles['Effective_boys_Age'] <= girl_age + 5) &
        (boys_profiles['Cast'] == girl['Cast']) &
        (boys_profiles['City'] == girl['City']) &
        (boys_profiles['Education_Level'] == girl_education_level)
    ]

    # Include additional columns in the displayed results
    return matches[['JIOID', 'Name', 'Cast', 'Marital Status', 'Height_cm', 'RealAge', 'City', 'Education', 'Salary-PA', 'Denomination', 'Occupation', 'joined', 'expire_date', 'Mobile']]

# Filter matches for a boy
def filter_matches_for_boy(boy, girls_profiles):
    """Filters girls profiles based on the given boy's criteria."""
    boy_education_level = map_education_level(boy['Education'])
    girls_profiles['Education_Level'] = girls_profiles['Education'].apply(map_education_level)

    matches = girls_profiles[
        (girls_profiles['Height_cm'] < boy['Height_cm']) &
        (girls_profiles['Marital Status'] == boy['Marital Status']) &
        (girls_profiles['RealAge'] < boy['RealAge']) &
        (girls_profiles['Cast'] == boy['Cast']) &
        (girls_profiles['City'] == boy['City']) &
        (girls_profiles['Education_Level'] == boy_education_level)
    ]

    # Include additional columns in the displayed results
    return matches[['JIOID', 'Name', 'Cast', 'Marital Status', 'Height_cm', 'RealAge', 'City', 'Education', 'Salary-PA', 'Denomination', 'Occupation', 'joined', 'expire_date', 'Mobile']]

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
    
    # File uploader widget
    file_path = st.file_uploader("Upload an Excel file", type=["xlsx"])
    
    if file_path is not None:
        # Load and preprocess data
        data = load_data(file_path)

        # Debugging: Display actual column names
        st.write("Columns in the uploaded file:", data.columns.tolist())

        # Adjust column names: Remove leading/trailing spaces, and make lowercase
        data.columns = data.columns.str.strip()
        data.columns = data.columns.str.lower()

        # Preprocess data
        data = preprocess_data(data)

        # Try accessing columns and handle KeyError
        try:
            profiles = data[['jioid', 'name', 'cast', 'marital status', 'hight/ft', 'realage', 'bride/bridegroom', 
                             'city', 'age', 'education', 'salary-pa', 'denomination', 'occupation', 'joined', 'expire_date', 'mobile']]
        except KeyError as e:
            st.error(f"KeyError: The following columns are missing: {e}")
            return

        profiles['jioid'] = profiles['jioid'].astype(str)

        girls_profiles, boys_profiles = split_profiles(profiles)

        # Input for profile ID
        input_id = st.text_input("Enter the JIOID of the profile to match:")

        if st.button("Find Matches"):
            if input_id in girls_profiles['jioid'].values:
                selected_profile = girls_profiles[girls_profiles['jioid'] == input_id].iloc[0]
                matches = filter_matches_for_girl(selected_profile, boys_profiles)
            elif input_id in boys_profiles['jioid'].values:
                selected_profile = boys_profiles[boys_profiles['jioid'] == input_id].iloc[0]
                matches = filter_matches_for_boy(selected_profile, girls_profiles)
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
                st.success(f"Matched profiles have been saved in the '{output_directory}' directory.")

if __name__ == "__main__":
    main()
