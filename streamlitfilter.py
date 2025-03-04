import streamlit as st
import sqlite3
import pandas as pd

# Database connection
def get_connection():
    conn = sqlite3.connect("doctors.db")
    return conn

# Create tables if they don't exist
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS specialties (
            specialty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS doctor_specialties (
            doctor_id TEXT,
            specialty_id TEXT,
            min_age INTEGER,
            max_age INTEGER,
            PRIMARY KEY (doctor_id, specialty_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
            FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id)
        );

        CREATE TABLE IF NOT EXISTS doctor_schedule (
            doctor_id TEXT,
            location TEXT NOT NULL,
            day_of_week TEXT NOT NULL CHECK(day_of_week IN 
                ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')),
            PRIMARY KEY (doctor_id, day_of_week, location),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );
    ''')
    conn.commit()
    conn.close()

create_tables()

# Load data from SQL
def load_data():
    conn = get_connection()
    doctors = pd.read_sql("SELECT * FROM doctors", conn)
    specialties = pd.read_sql("SELECT * FROM specialties", conn)
    doctor_specialties = pd.read_sql("SELECT * FROM doctor_specialties", conn)
    schedule = pd.read_sql("SELECT * FROM doctor_schedule", conn)
    conn.close()
    return doctors, specialties, doctor_specialties, schedule

doctors, specialties, doctor_specialties, schedule = load_data()

# Streamlit UI
st.title("Doctor Filter App")

# Filters
doctor_filter = st.multiselect("Select Doctor(s)", doctors['name'].tolist())
specialty_filter = st.multiselect("Select Specialty(ies)", specialties['name'].tolist())
location_filter = st.multiselect("Select Location(s)", schedule['location'].unique().tolist())
day_filter = st.multiselect("Select Day(s)", schedule['day_of_week'].unique().tolist())
age_filter = st.number_input("Enter Patient Age", min_value=0, max_value=100, value=30)

# Start filtering with all doctors
filtered_doctors = doctors.copy()

if doctor_filter:
    filtered_doctors = filtered_doctors[filtered_doctors['name'].isin(doctor_filter)]

if specialty_filter:
    filtered_specialties = specialties[specialties['name'].isin(specialty_filter)]
    doctor_specialties_filtered = doctor_specialties[doctor_specialties['specialty_id'].isin(filtered_specialties['specialty_id'])]
    
    # Ensure selected age is within the allowed range
    doctor_specialties_filtered = doctor_specialties_filtered[
        (doctor_specialties_filtered['min_age'] <= age_filter) & 
        (doctor_specialties_filtered['max_age'] >= age_filter)
    ]
    
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(doctor_specialties_filtered['doctor_id'])]

if location_filter:
    valid_doctors = schedule[schedule['location'].isin(location_filter)]['doctor_id'].unique()
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

if day_filter:
    valid_doctors = schedule[schedule['day_of_week'].isin(day_filter)]['doctor_id'].unique()
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

# Merge filtered doctors with schedules and specialties
filtered_schedule = schedule[schedule['doctor_id'].isin(filtered_doctors['doctor_id'])]
filtered_specialties = doctor_specialties[doctor_specialties['doctor_id'].isin(filtered_doctors['doctor_id'])]

# Merge data for display
merged_data = filtered_doctors.merge(filtered_schedule, on='doctor_id', how='inner')
merged_data = merged_data.merge(filtered_specialties, on='doctor_id', how='inner')
merged_data = merged_data.merge(specialties, on='specialty_id', how='inner', suffixes=('_doc', '_spec'))

# Select relevant columns for display
filtered_data = merged_data[['doctor_id', 'name_doc', 'day_of_week', 'location', 'name_spec']]
filtered_data = filtered_data.rename(columns={'name_doc': 'Name', 'name_spec': 'Specialty'})

# Show filtered results
st.write("### Available Doctors:")
st.dataframe(filtered_data)
