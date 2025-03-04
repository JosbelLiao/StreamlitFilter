import streamlit as st
import sqlite3
import pandas as pd

# Database connection
def get_connection():
    return sqlite3.connect("doctors.db")

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
doctor_filter = st.multiselect("Select Doctor(s)", doctors['name'].tolist(), default=doctors['name'].tolist())
specialty_filter = st.multiselect("Select Specialty(ies)", specialties['name'].tolist(), default=specialties['name'].tolist())
location_filter = st.multiselect("Select Location(s)", schedule['location'].unique().tolist(), default=schedule['location'].unique().tolist())
day_filter = st.multiselect("Select Day(s)", schedule['day_of_week'].unique().tolist(), default=schedule['day_of_week'].unique().tolist())
age_filter = st.number_input("Enter Patient Age", min_value=0, max_value=100, value=30)

# Filtering Logic
filtered_doctors = doctors[doctors['name'].isin(doctor_filter)]

if specialty_filter:
    specialty_ids = specialties[specialties['name'].isin(specialty_filter)]['specialty_id']
    doctor_specialties_filtered = doctor_specialties[doctor_specialties['specialty_id'].isin(specialty_ids)]
    valid_doctors = doctor_specialties_filtered[
        (doctor_specialties_filtered['min_age'] <= age_filter) & (doctor_specialties_filtered['max_age'] >= age_filter)
    ]['doctor_id']
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

if location_filter:
    valid_doctors = schedule[schedule['location'].isin(location_filter)]['doctor_id']
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

if day_filter:
    valid_doctors = schedule[schedule['day_of_week'].isin(day_filter)]['doctor_id']
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

# Merging details for display
filtered_details = filtered_doctors.merge(doctor_specialties, on='doctor_id', how='left')
filtered_details = filtered_details.merge(specialties, on='specialty_id', how='left')
filtered_details = filtered_details.merge(schedule, on='doctor_id', how='left')
filtered_details = filtered_details[['doctor_id', 'name', 'day_of_week', 'location', 'specialty_id', 'name_y']]
filtered_details.rename(columns={'name_y': 'specialty'}, inplace=True)

st.write("### Available Doctors:")
st.dataframe(filtered_details)
