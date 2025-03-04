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
doctor_filter = st.selectbox("Select Doctor", ["All"] + doctors['name'].tolist())
specialty_filter = st.selectbox("Select Specialty", ["All"] + specialties['name'].tolist())
day_filter = st.selectbox("Select Day", ["All"] + schedule['day_of_week'].unique().tolist())
age_filter = st.number_input("Enter Patient Age", min_value=0, max_value=100, value=30)

# Filter logic
filtered_doctors = doctors.copy()

if doctor_filter != "All":
    filtered_doctors = filtered_doctors[filtered_doctors['name'] == doctor_filter]

if specialty_filter != "All":
    doctor_specialties_filtered = doctor_specialties[doctor_specialties['specialty_id'] == 
        specialties[specialties['name'] == specialty_filter]['specialty_id'].values[0]]
    
    min_age = doctor_specialties_filtered['min_age'].min()
    max_age = doctor_specialties_filtered['max_age'].max()
    
    if not (min_age <= age_filter <= max_age):
        st.warning(f"This specialty is only available for ages {min_age} to {max_age}.")
    
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(doctor_specialties_filtered['doctor_id'])]

if day_filter != "All":
    valid_doctors = schedule[schedule['day_of_week'] == day_filter]['doctor_id'].tolist()
    filtered_doctors = filtered_doctors[filtered_doctors['doctor_id'].isin(valid_doctors)]

st.write("### Available Doctors:")
st.dataframe(filtered_doctors)

# Data Entry Forms
st.sidebar.title("Manage Database")
conn = get_connection()

# Add Doctor
with st.sidebar.form("add_doctor"):
    st.subheader("Add Doctor")
    doctor_id = st.text_input("Doctor ID")
    doctor_name = st.text_input("Doctor Name")
    if st.form_submit_button("Add Doctor"):
        conn.execute("INSERT INTO doctors (doctor_id, name) VALUES (?, ?)", (doctor_id, doctor_name))
        conn.commit()
        st.success("Doctor added successfully")

# Add Specialty
with st.sidebar.form("add_specialty"):
    st.subheader("Add Specialty")
    specialty_id = st.text_input("Specialty ID")
    specialty_name = st.text_input("Specialty Name")
    if st.form_submit_button("Add Specialty"):
        conn.execute("INSERT INTO specialties (specialty_id, name) VALUES (?, ?)", (specialty_id, specialty_name))
        conn.commit()
        st.success("Specialty added successfully")

# Assign Doctor to Specialty with Age Restrictions
with st.sidebar.form("assign_specialty"):
    st.subheader("Assign Specialty to Doctor")
    selected_doctor = st.selectbox("Select Doctor", doctors['doctor_id'].tolist())
    selected_specialty = st.selectbox("Select Specialty", specialties['specialty_id'].tolist())
    min_age = st.number_input("Min Age", min_value=0, max_value=100, value=0)
    max_age = st.number_input("Max Age", min_value=0, max_value=100, value=100)
    if st.form_submit_button("Assign Specialty"):
        conn.execute("INSERT INTO doctor_specialties (doctor_id, specialty_id, min_age, max_age) VALUES (?, ?, ?, ?)", 
                     (selected_doctor, selected_specialty, min_age, max_age))
        conn.commit()
        st.success("Specialty assigned successfully")

# Assign Doctor to Schedule
with st.sidebar.form("assign_schedule"):
    st.subheader("Assign Doctor Schedule")
    selected_doctor = st.selectbox("Select Doctor for Schedule", doctors['doctor_id'].tolist(), key="schedule_doctor")
    location = st.text_input("Location")
    day_of_week = st.selectbox("Day of the Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    if st.form_submit_button("Assign Schedule"):
        conn.execute("INSERT INTO doctor_schedule (doctor_id, location, day_of_week) VALUES (?, ?, ?)", 
                     (selected_doctor, location, day_of_week))
        conn.commit()
        st.success("Schedule assigned successfully")

conn.close()
