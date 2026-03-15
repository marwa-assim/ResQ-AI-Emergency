import os
print("Working directory:", os.getcwd())


import random
import csv

NUM_SAMPLES = 5000

def label_case(case):
    age = case['age']
    hr = case['heart_rate']
    spo2 = case['spo2']
    temp = case['temperature']
    chest = case['chest_pain']
    breath = case['breathing_difficulty']
    bleed = case['bleeding']
    faint = case['fainting']
    arrival = case['arrival_mode']
    chronic = case['chronic_disease']

    # RED
    if spo2 < 90:
        return 3
    if hr > 130 and (chest or breath):
        return 3
    if faint and age >= 60:
        return 3
    if bleed and hr > 120:
        return 3

    # ORANGE
    if 90 <= spo2 < 94:
        return 2
    if hr >= 110:
        return 2
    if temp >= 39.0 and breath:
        return 2
    if age >= 65 and (chest or breath):
        return 2
    if arrival == 2 and (chest or breath or bleed or faint):
        return 2

    # YELLOW
    if temp >= 37.5:
        return 1
    if 100 <= hr < 110:
        return 1
    if chronic:
        return 1

    # GREEN
    return 0

with open(os.path.join(os.path.dirname(__file__), 'triage_data.csv'), 'w', newline='') as f:

    writer = csv.writer(f)
    header = [
        'age','arrival_mode','heart_rate','spo2','temperature',
        'chest_pain','breathing_difficulty','bleeding','fainting',
        'chronic_disease','allergy_risk','label'
    ]
    writer.writerow(header)

    for _ in range(NUM_SAMPLES):
        case = {
            'age': random.randint(1, 95),
            'arrival_mode': random.choice([0,1,2]),
            'heart_rate': random.randint(50, 160),
            'spo2': random.randint(85, 100),
            'temperature': round(random.uniform(36.0, 40.5), 1),
            'chest_pain': random.choice([0,1]),
            'breathing_difficulty': random.choice([0,1]),
            'bleeding': random.choice([0,1]),
            'fainting': random.choice([0,1]),
            'chronic_disease': random.choice([0,1]),
            'allergy_risk': random.choice([0,1]),
        }
        label = label_case(case)
        writer.writerow(list(case.values()) + [label])

print("Generated triage_data.csv")
