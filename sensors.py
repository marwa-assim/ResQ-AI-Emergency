import random

def read_heart_rate():
    return random.randint(60, 140)

def read_spo2():
    return random.randint(85, 100)

def read_temperature():
    return round(random.uniform(36.0, 39.5), 1)
