def generate_arabic_name():
    first = ["Ahmed", "Mohamed", "Ali", "Fatima", "Noor", "Sara", "Khalid", "Omar", "Layla", "Yousef"]
    last = ["Al-Saud", "Al-Harbi", "Al-Otaibi", "Al-Ghamdi", "Al-Amri", "Khan", "Malik", "Salem"]
    return f"{random.choice(first)} {random.choice(last)}"
