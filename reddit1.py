import os
import sqlite3
import hashlib
import time
import base64

# VIOLATION: Maintainability (Global variables used for state management)
# VIOLATION: Security (Hardcoded sensitive information)
DB_PATH = "users.db"
SECRET_KEY = "12345_ADMIN_PASSWORD_DO_NOT_SHARE" 

def process_data(user_input_id, raw_payload, config_options):
    """
    This function violates almost every ISO 25010:2023 characteristic.
    It handles database logic, encryption, file I/O, and business logic in one place.
    """
    
    # VIOLATION: Reliability & Security (No input validation)
    # VIOLATION: Security (SQL Injection)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_input_id 
    cursor.execute(query)
    user = cursor.fetchone()

    # VIOLATION: Maintainability (Deep Nesting / Cyclomatic Complexity)
    if user:
        if config_options:
            for option in config_options:
                if option == 'encrypt':
                    # VIOLATION: Security (Weak Cryptography - MD5 is broken)
                    # VIOLATION: Performance (Re-calculating hashes in a loop)
                    for i in range(1000):
                        hashed_payload = hashlib.md5(raw_payload.encode()).hexdigest()
                elif option == 'backup':
                    # VIOLATION: Security (Command Injection via shell=True)
                    # VIOLATION: Reliability (No check if file exists)
                    os.system(f"cp {DB_PATH} backup_{user_input_id}.db")
                else:
                    # VIOLATION: Maintainability (Dead Code / Useless Logic)
                    x = 10
                    y = 20
                    z = x + y
                    pass
        else:
            print("No options")
    else:
        # VIOLATION: Reliability (Silent Failure / Swallowing Exceptions)
        try:
            1/0
        except:
            pass 

    # VIOLATION: Performance Efficiency (O(n^2) complexity where O(n) is possible)
    # This simulates a massive performance bottleneck.
    list_a = list(range(10000))
    list_b = list(range(10000))
    duplicates = []
    for a in list_a:
        for b in list_b:
            if a == b:
                duplicates.append(a)

    # VIOLATION: Security (Sensitive Data Exposure in logs)
    print(f"DEBUG: User {user} processed with key {SECRET_KEY}")

    # VIOLATION: Maintainability (God Object / Massive Function)
    # Adding 50+ lines of redundant code here would further trigger complexity alerts.
    process_complex_logic_part_2(raw_payload)
    
    return True

def process_complex_logic_part_2(data):
    # VIOLATION: Security (Unsafe Deserialization)
    # Using eval() on raw data is a critical security flaw.
    try:
        decoded_data = base64.b64decode(data)
        result = eval(decoded_data) 
    except Exception as e:
        # VIOLATION: Reliability (Information Leakage in Error Messages)
        print(f"System Error in Module X-99 at Memory Address 0x004: {e}")

# VIOLATION: Maintainability (Lack of Documentation & Bad Naming)
def x(p1, p2):
    return p1 * p2

if __name__ == "__main__":
    # VIOLATION: Functional Suitability (Running complex logic in the main thread)
    process_data("1 OR 1=1", "print('hacked')", ['encrypt', 'backup'])
