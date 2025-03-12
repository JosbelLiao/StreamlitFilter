import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Obtener la URL de la base de datos desde las variables de entorno
database_url = os.getenv("DATABASE_URL")

# Función para obtener la conexión a la base de datos
def get_connection():
    conn = psycopg2.connect(database_url)
    return conn

# Create tables if they don't exist
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    commands = [
        '''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        ''',
        '''
        CREATE TABLE IF NOT EXISTS specialties (
            specialty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        ''',
        '''
        CREATE TABLE IF NOT EXISTS doctor_specialties (
            doctor_id TEXT,
            specialty_id TEXT,
            min_age INTEGER,
            max_age INTEGER,
            PRIMARY KEY (doctor_id, specialty_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
            FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id)
        );
        ''',
        '''
        CREATE TABLE IF NOT EXISTS doctor_schedule (
            doctor_id TEXT,
            location TEXT NOT NULL,
            day_of_week TEXT NOT NULL CHECK(day_of_week IN 
                ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')),
            PRIMARY KEY (doctor_id, day_of_week, location),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );
        '''
    ]
    for command in commands:
        cursor.execute(command)
    conn.commit()
    cursor.close()
    conn.close()

# Call function create_tables to create tables
create_tables()


# Load data from SQL
def load_data():
    conn = get_connection()
    doctors = pd.read_sql("SELECT * FROM doctors", conn)
    specialties = pd.read_sql("SELECT * FROM specialties", conn)
    doctor_specialties = pd.read_sql("SELECT * FROM doctor_specialties", conn)
    schedule = pd.read_sql("SELECT * FROM doctor_schedule", conn)
    conn.close()

    # Handle None values for min_age and max_age
    doctor_specialties['min_age'].fillna(0, inplace=True)
    doctor_specialties['max_age'].fillna(150, inplace=True)

    return doctors, specialties, doctor_specialties, schedule

doctors, specialties, doctor_specialties, schedule = load_data()

# Streamlit UI
st.title("Doctor Filter App")

# Filters
doctor_filter = st.multiselect("Select Doctor", doctors['name'].tolist(), default=doctors['name'].tolist())
specialty_filter = st.multiselect("Select Specialty", specialties['name'].tolist(), default=specialties['name'].tolist())
location_filter = st.multiselect("Select Location", schedule['location'].unique().tolist(), default=schedule['location'].unique().tolist())
day_filter = st.multiselect("Select Day", schedule['day_of_week'].unique().tolist(), default=schedule['day_of_week'].unique().tolist())
age_filter = st.number_input("Enter Patient Age", min_value=0, max_value=100, value=30)

# Filter logic
filtered_doctors = doctors.copy()

if doctor_filter:
    filtered_doctors = filtered_doctors[filtered_doctors['name'].isin(doctor_filter)]

if specialty_filter:
    doctor_specialties_filtered = doctor_specialties[doctor_specialties['specialty_id'].isin(
        specialties[specialties['name'].isin(specialty_filter)]['specialty_id'].values)]
    
    min_age = doctor_specialties_filtered['min_age'].min()
    max_age = doctor_specialties_filtered['max_age'].max()
    
    if min_age is not None and max_age is not None:
        if not (min_age <= age_filter <= max_age):
            st.warning(f"This specialty is only available for ages {min_age} to {max_age}.")
    elif min_age is not None and max_age is None:
        if age_filter < min_age:
            st.warning(f"This specialty is only available for ages {min_age} and above.")
    elif min_age is None and max_age is not None:
        if age_filter > max_age:
            st.warning(f"This specialty is only available for ages {max_age} and below.")
    
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(doctor_specialties_filtered['doctor_id'])]

if location_filter:
    valid_doctors = schedule[schedule['location'].isin(location_filter)]['doctor_id'].tolist()
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

if day_filter:
    valid_doctors = schedule[schedule['day_of_week'].isin(day_filter)]['doctor_id'].tolist()
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

# Merge additional details for display
filtered_doctors = filtered_doctors.merge(doctor_specialties, on='doctor_id', how='left')
filtered_doctors = filtered_doctors.merge(schedule, on='doctor_id', how='left')
filtered_doctors = filtered_doctors.merge(specialties, on='specialty_id', how='left', suffixes=('', '_specialty'))

# Filter merged results based on the selected filters
if specialty_filter:
    filtered_doctors = filtered_doctors[filtered_doctors['name_specialty'].isin(specialty_filter)]

if location_filter:
    filtered_doctors = filtered_doctors[filtered_doctors['location'].isin(location_filter)]

if day_filter:
    filtered_doctors = filtered_doctors[filtered_doctors['day_of_week'].isin(day_filter)]

# Display the table with additional details
st.write("### Available Doctors:")
st.dataframe(filtered_doctors[['name', 'location', 'day_of_week', 'name_specialty']])

# Data Entry Forms
st.sidebar.title("Manage Database")
conn = get_connection()

# Add Doctor
with st.sidebar.form("add_doctor"):
    st.subheader("Add Doctor")
    doctor_id = st.text_input("Doctor ID")
    doctor_name = st.text_input("Doctor Name")
    if st.form_submit_button("Add Doctor"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO doctors (doctor_id, name) VALUES (%s, %s)", (doctor_id, doctor_name))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Doctor added successfully")

# Add Specialty
with st.sidebar.form("add_specialty"):
    st.subheader("Add Specialty")
    specialty_id = st.text_input("Specialty ID")
    specialty_name = st.text_input("Specialty Name")
    if st.form_submit_button("Add Specialty"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO specialties (specialty_id, name) VALUES (%s, %s)", (specialty_id, specialty_name))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Specialty added successfully")

# Assign Doctor to Specialty with Age Restrictions
with st.sidebar.form("assign_specialty"):
    st.subheader("Assign Specialty to Doctor")
    selected_doctor = st.selectbox("Select Doctor", doctors['doctor_id'].tolist())
    selected_specialty = st.selectbox("Select Specialty", specialties['specialty_id'].tolist())
    min_age = st.number_input("Min Age", min_value=0, max_value=150, value=None)  # Allow None
    max_age = st.number_input("Max Age", min_value=0, max_value=150, value=None)  # Allow None
    if st.form_submit_button("Assign Specialty"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO doctor_specialties (doctor_id, specialty_id, min_age, max_age) VALUES (%s, %s, %s, %s)", 
                       (selected_doctor, selected_specialty, min_age, max_age))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Specialty assigned successfully")

# Assign Doctor to Schedule
with st.sidebar.form("assign_schedule"):
    st.subheader("Assign Doctor Schedule")
    selected_doctor = st.selectbox("Select Doctor for Schedule", doctors.set_index('doctor_id')['name'].to_dict(), key="schedule_doctor")
    location = st.text_input("Location")
    day_of_week = st.selectbox("Day of the Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    if st.form_submit_button("Assign Schedule"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO doctor_schedule (doctor_id, location, day_of_week) VALUES (%s, %s, %s)", 
                       (selected_doctor, location, day_of_week))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Schedule assigned successfully")

# Update Doctor Information
with st.sidebar.form("update_doctor"):
    st.subheader("Update Doctor")
    update_doctor_id = st.selectbox("Select Doctor to Update", doctors.set_index('doctor_id')['name'].to_dict())
    selected_specialty = st.selectbox("Select Specialty to Update", specialties.set_index('specialty_id')['name'].to_dict(), key="update_specialty")
    new_name = st.text_input("New Doctor Name")
    new_day_of_week = st.selectbox("Select Day of the Week to Update", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="update_day_of_week")
    new_location = st.text_input("New Location")
    new_min_age = st.number_input("New Min Age", min_value=0, max_value=100, value=0)
    new_max_age = st.number_input("New Max Age", min_value=0, max_value=100, value=100)
    if st.form_submit_button("Update Doctor"):
        conn = get_connection()
        cursor = conn.cursor()
        # Update doctor's name (if necessary)
        if new_name:
            cursor.execute('''
                UPDATE doctors
                SET name = %s
                WHERE doctor_id = %s
            ''', (new_name, update_doctor_id))

        # Update age restrictions for the specific specialty (if necessary)
        if new_min_age is not None and new_max_age is not None:
            cursor.execute('''
                UPDATE doctor_specialties
                SET min_age = %s, max_age = %s
                WHERE doctor_id = %s AND specialty_id = %s
            ''', (new_min_age, new_max_age, update_doctor_id, selected_specialty))

        # Update doctor's location for the specific day (if necessary)
        if new_location:
            cursor.execute('''
                UPDATE doctor_schedule
                SET location = %s
                WHERE doctor_id = %s AND day_of_week = %s
            ''', (new_location, update_doctor_id, new_day_of_week))

        conn.commit()
        cursor.close()
        conn.close()
        st.success("Doctor updated successfully")

# Remove Specialty from Doctor
with st.sidebar.form("remove_specialty"):
    st.subheader("Remove Specialty from Doctor")
    selected_doctor_specialty = st.selectbox("Select Doctor to Remove Specialty From", doctors['doctor_id'].tolist())
    selected_specialty_remove = st.selectbox("Select Specialty to Remove", specialties['specialty_id'].tolist(), key="remove_specialty")
    if st.form_submit_button("Remove Specialty"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM doctor_specialties WHERE doctor_id = %s AND specialty_id = %s", 
                       (selected_doctor_specialty, selected_specialty_remove))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Specialty removed successfully")

# Remove Day from Doctor's Schedule
with st.sidebar.form("remove_day"):
    st.subheader("Remove Day from Doctor's Schedule")
    selected_doctor_day = st.selectbox("Select Doctor to Remove Day From", doctors['doctor_id'].tolist(), key="remove_day_doctor")
    selected_day_remove = st.selectbox("Select Day to Remove from Schedule", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="remove_day_schedule")
    if st.form_submit_button("Remove Day"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM doctor_schedule WHERE doctor_id = %s AND day_of_week = %s", 
                       (selected_doctor_day, selected_day_remove))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Day removed successfully")


conn.close()
