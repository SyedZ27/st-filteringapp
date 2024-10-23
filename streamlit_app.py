import streamlit as st
import pandas as pd
import os

# Load the Excel file
def load_data(file_path):
    """Loads data from an Excel file into a pandas DataFrame."""
    return pd.read_excel(file_path)

# Convert height to cm
def convert_height_to_cm(height_str):
    """Converts height given in different string formats to centimeters."""
    if pd.isnull(height_str):
        return None

    if isinstance(height_str, (int, float)):
        return height_str

    height_str = str(height_str).lower().strip()

    if 'ft' in height_str and '-' in height_str:
        try:
            feet_inches = height_str.split('-')[0].strip()
            feet, inches = feet_inches.split('ft')
            inches = inches.replace('in', '').strip()
            return int(feet.strip()) * 30.48 + int(inches) * 2.54
        except ValueError:
            return None

    if 'cm' in height_str:
        try:
            return float(height_str.replace('cm', '').strip())
        except ValueError:
            return None

    if 'ft' in height_str:
        try:
            feet_inches = height_str.split('ft')
            feet = feet_inches[0].strip()
            inches = feet_inches[1].replace('in', '').strip() if len(feet_inches) > 1 else '0'
            return int(feet) * 30.48 + int(inches) * 2.54
        except ValueError:
            return None

    return None

# Clean salary strings
def clean_salary(salary_str):
    """Cleans and standardizes salary values from strings like '5 LPA'."""
    if pd.isnull(salary_str) or str(salary_str).strip().upper() == 'NA':
        return None
    salary_str = str(salary_str).replace(' ', '').upper()
    try:
        if 'LPA' in salary_str:
            salary_value = float(salary_str.replace('LPA', '').strip())
            return salary_value
        else:
            return float(salary_str.strip())
    except ValueError:
        return None

# Clean and preprocess data with updated column names
def preprocess_data_updated(data):
    """Cleans and preprocesses the raw data with updated column names."""
    # Strip leading and trailing spaces from column names
    data.columns = data.columns.str.strip()

    # Handling 'Age' column directly
    data['Age'] = data['Age'].fillna(0).astype(str).str.strip()
    data['Age'] = pd.to_numeric(data['Age'], errors='coerce').fillna(0).astype(int)

    # Standardize 'gender' column
    if 'gender' in data.columns:
        data['gender'] = data['gender'].str.lower().str.strip()

    # Clean and standardize salary column
    if 'Salary-PA_Standardized' in data.columns:
        data['Salary-PA_Standardized'] = data['Salary-PA_Standardized'].apply(clean_salary)
    else:
        st.error("'Salary-PA_Standardized' column not found in the data.")

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
        return education_hierarchy.get(education.lower().strip(), 0)
    return 0

def filter_matches_for_boy_updated(boy, girls_profiles):
    boy_age = int(boy['Age']) if pd.notna(boy['Age']) else None
    girls_profiles['Effective_girls_Age'] = girls_profiles['Age'].fillna(0).astype(int)

    boy_education_level = map_education_level(boy['Education_Standardized'])
    girls_profiles['Education_Level'] = girls_profiles['Education_Standardized'].apply(map_education_level)

    # Clean salary values for comparison
    boy_salary = boy['Salary-PA_Standardized']
    girls_profiles['Salary_Cleaned'] = girls_profiles['Salary-PA_Standardized']

    # Apply the matching criteria for boys
    matches = girls_profiles[
        ((girls_profiles['Hight/CM'] < boy['Hight/CM']) & pd.notna(girls_profiles['Hight/CM']) & pd.notna(boy['Hight/CM'])) &
        ((girls_profiles['Marital Status'] == boy['Marital Status']) | pd.isnull(boy['Marital Status'])) &
        ((girls_profiles['Effective_girls_Age'] >= boy_age - 5) & (girls_profiles['Effective_girls_Age'] <= boy_age)) &
        (girls_profiles['Education_Level'] <= boy_education_level) & pd.notna(girls_profiles['Education_Level']) & pd.notna(boy['Education_Standardized']) &
        ((girls_profiles['Salary_Cleaned'] <= boy_salary) | pd.isnull(girls_profiles['Salary_Cleaned']) | pd.isnull(boy_salary))
    ]

    return matches

def filter_matches_for_girl_updated(girl, boys_profiles):
    girl_age = int(girl['Age']) if pd.notna(girl['Age']) else None
    boys_profiles['Effective_boys_Age'] = boys_profiles['Age'].fillna(0).astype(int)

    girl_education_level = map_education_level(girl['Education_Standardized'])
    boys_profiles['Education_Level'] = boys_profiles['Education_Standardized'].apply(map_education_level)

    # Clean salary values for comparison
    girl_salary = girl['Salary-PA_Standardized']
    boys_profiles['Salary_Cleaned'] = boys_profiles['Salary-PA_Standardized']

    # Apply the matching criteria for girls
    matches = boys_profiles[
        ((boys_profiles['Hight/CM'] > girl['Hight/CM']) & pd.notna(boys_profiles['Hight/CM']) & pd.notna(girl['Hight/CM'])) &
        ((boys_profiles['Marital Status'] == girl['Marital Status']) | pd.isnull(girl['Marital Status'])) &
        ((boys_profiles['Effective_boys_Age'] >= girl_age) & (boys_profiles['Effective_boys_Age'] <= girl_age + 5)) &
        (boys_profiles['Education_Level'] >= girl_education_level) & pd.notna(boys_profiles['Education_Level']) & pd.notna(girl['Education_Standardized']) &
        ((boys_profiles['Salary_Cleaned'] >= girl_salary) | pd.isnull(boys_profiles['Salary_Cleaned']) | pd.isnull(girl_salary))
    ]

    return matches

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
                                'City', 'Age', 'Education_Standardized', 'Salary-PA_Standardized', 'Denomination',
                                'Occupation', 'joined', 'expire_date', 'Mobile']

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

                    # Provide download option for matched profiles
                    output_directory = st.text_input("Enter output directory to save CSV files:")
                    if st.button("Save Matches to CSV"):
                        if not os.path.exists(output_directory):
                            st.error("Output directory does not exist.")
                        else:
                            csv_file_path = save_matches_to_csv(selected_profile, matches, output_directory)
                            st.success(f"Matches saved to {csv_file_path}.")

                elif selected_jioid in girls_profiles['JIOID'].values:
                    selected_profile = girls_profiles[girls_profiles['JIOID'] == selected_jioid].iloc[0]
                    matches = filter_matches_for_girl_updated(selected_profile, boys_profiles)

                    # Display the number of matches for the girl
                    num_matches = len(matches)
                    st.write(f"{num_matches} profiles matched for girl {selected_profile['Name']}:")
                    st.dataframe(matches)

                    # Provide download option for matched profiles
                    output_directory = st.text_input("Enter output directory to save CSV files:")
                    if st.button("Save Matches to CSV"):
                        if not os.path.exists(output_directory):
                            st.error("Output directory does not exist.")
                        else:
                            csv_file_path = save_matches_to_csv(selected_profile, matches, output_directory)
                            st.success(f"Matches saved to {csv_file_path}.")
                else:
                    st.error(f"No profile found for JIOID: {selected_jioid}")

        except Exception as e:
            st.error(f"Error loading or processing the file: {e}")

if __name__ == "__main__":
    main()
