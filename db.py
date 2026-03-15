import sqlite3

DB_NAME = "patients.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Drop table for fresh start with new schema (Demo purposes)
    c.execute("DROP TABLE IF EXISTS patients")

    c.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id TEXT PRIMARY KEY,
        name TEXT,
        age INTEGER,
        chronic INTEGER,
        allergy INTEGER,
        visits INTEGER DEFAULT 1
    )
    """)

    # Seed demo data
    seed_data = [
        ("1001", "Sara Ahmed", 45, 1, 0),
        ("1002", "Mariam Samer", 29, 0, 1),
        ("1003", "Fatima Raed", 65, 1, 0),
        ("1004", "Suzan James", 34, 0, 0)
    ]
    
    for pid, name, age, chr_flag, alg_flag in seed_data:
        c.execute("INSERT OR REPLACE INTO patients (patient_id, name, age, chronic, allergy) VALUES (?, ?, ?, ?, ?)", 
                  (pid, name, age, chr_flag, alg_flag))

    conn.commit()
    conn.close()

def get_patient(patient_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM patients WHERE patient_id=?", (patient_id,))
    row = c.fetchone()
    conn.close()

    # Returns: (id, name, age, chronic, allergy, visits)
    return row

def save_patient(patient_id, name, age, chronic, allergy):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    existing = get_patient(patient_id)
    if existing:
        c.execute("""
        UPDATE patients
        SET visits = visits + 1, age=?, chronic=?, allergy=?
        WHERE patient_id=?
        """, (age, chronic, allergy, patient_id))
    else:
        c.execute("""
        INSERT INTO patients (patient_id, name, age, chronic, allergy)
        VALUES (?, ?, ?, ?, ?)
        """, (patient_id, name, age, chronic, allergy))

    conn.commit()
    conn.close()
