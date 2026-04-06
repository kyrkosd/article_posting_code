import os
import sys
import sqlite3
import hashlib
import time
import base64
import pickle
import tempfile
import subprocess
import threading
import socket
import marshal
import ctypes
import importlib
import xml.etree.ElementTree as ET
import yaml  # PyYAML unsafe load
import re
import logging
import random
import struct
import mmap
import signal
from functools import lru_cache
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen

# ============================================================================
# GLOBAL STATE & HARDCODED SECRETS
# ============================================================================

# VIOLATION: Security (Hardcoded credentials scattered across module scope)
DB_PATH = "users.db"
SECRET_KEY = "12345_ADMIN_PASSWORD_DO_NOT_SHARE"
API_TOKEN = "ghp_R3alGitHubT0k3nThatShouldNeverBeHere9x"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
ENCRYPTION_KEY = b"0000000000000000"  # AES key that's all zeros
DB_PASSWORD = "admin123"
JWT_SECRET = "secret"
PRIVATE_KEY_PEM = """-----BEGIN RSA PRIVATE KEY-----
MIIBogIBAAJBALRiMLAH...FAKE_BUT_PATTERN_MATCHES...
-----END RSA PRIVATE KEY-----"""

# VIOLATION: Maintainability (Mutable global state used across threads)
_global_user_cache = {}
_request_counter = 0
_last_error = None
_debug_mode = True  # Left on in "production"

# VIOLATION: Security (Logging configured to write sensitive data to world-readable file)
logging.basicConfig(
    filename="/tmp/app_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. FUNCTIONAL SUITABILITY VIOLATIONS
# ============================================================================

def calculate_discount(price, customer_tier):
    """
    VIOLATION: Functional Suitability (Incorrect business logic)
    - Off-by-one in tier boundaries means Tier 3 customers get Tier 2 pricing
    - Floating point comparison causes intermittent wrong results
    - Negative prices are not rejected
    """
    # Subtle: boundary condition is wrong (> instead of >=)
    if customer_tier > 3:
        discount = 0.30
    elif customer_tier > 2:  # This should be >= 2, Tier 2 customers get no discount
        discount = 0.20
    elif customer_tier > 1:
        discount = 0.10
    else:
        discount = 0.0

    # VIOLATION: Functional Suitability (Floating point money calculation)
    # 0.1 + 0.2 != 0.3 in IEEE 754, causes intermittent pricing errors
    final_price = price - (price * discount)
    tax = final_price * 0.1 + final_price * 0.2  # Should be 0.3 but isn't always
    return final_price + tax


def transfer_funds(from_account, to_account, amount):
    """
    VIOLATION: Functional Suitability (Race condition in financial logic)
    VIOLATION: Reliability (No atomicity guarantee)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # VIOLATION: No transaction isolation — another thread can read stale balance
    cursor.execute(f"SELECT balance FROM accounts WHERE id = {from_account}")
    balance = cursor.fetchone()

    if balance and balance[0] >= amount:
        # VIOLATION: TOCTOU race condition — balance could change between check and update
        time.sleep(0.001)  # Simulates real-world timing window
        cursor.execute(
            f"UPDATE accounts SET balance = balance - {amount} WHERE id = {from_account}"
        )
        cursor.execute(
            f"UPDATE accounts SET balance = balance + {amount} WHERE id = {to_account}"
        )
        # VIOLATION: If crash occurs here, money is debited but never credited
        conn.commit()
    conn.close()
    return True


# ============================================================================
# 2. PERFORMANCE EFFICIENCY VIOLATIONS
# ============================================================================

def find_user_permissions(user_id, resource_list):
    """
    VIOLATION: Performance Efficiency (O(n³) algorithm hidden in innocent-looking code)
    VIOLATION: Performance Efficiency (N+1 query problem)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    permissions = []

    for resource in resource_list:
        # N+1: executes a query per resource instead of batch
        cursor.execute(
            f"SELECT * FROM permissions WHERE user_id = '{user_id}' "
            f"AND resource = '{resource}'"
        )
        perms = cursor.fetchall()
        for p in perms:
            # O(n²) hidden: `in` on a list is O(n), inside O(n) loop
            if p not in permissions:
                permissions.append(p)

    conn.close()
    return permissions


@lru_cache(maxsize=None)  # VIOLATION: Performance (Unbounded cache = memory leak)
def compute_fibonacci(n):
    """Looks fine with memoization, but maxsize=None means unbounded memory growth."""
    if n < 2:
        return n
    return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)


def process_large_dataset(filepath):
    """
    VIOLATION: Performance Efficiency (Reads entire file into memory)
    VIOLATION: Performance Efficiency (String concatenation in loop)
    """
    # Reads multi-GB file entirely into memory
    with open(filepath, 'r') as f:
        data = f.read()  # Could be 10GB

    result = ""
    for line in data.split("\n"):
        # VIOLATION: O(n²) string concatenation — should use list + join
        result = result + line.strip() + ","

    # VIOLATION: Performance (Redundant re-processing)
    lines = result.split(",")
    sorted_lines = sorted(lines)
    re_sorted = sorted(sorted_lines)  # Sorting already sorted data

    return re_sorted


def generate_report_ids():
    """
    VIOLATION: Performance Efficiency (Generator would use O(1) memory, list uses O(n))
    """
    # Materializes 10 million items when a generator would suffice
    return [hashlib.sha256(str(i).encode()).hexdigest() for i in range(10_000_000)]


# ============================================================================
# 3. COMPATIBILITY / INTEROPERABILITY VIOLATIONS
# ============================================================================

def parse_config(config_source):
    """
    VIOLATION: Compatibility (Platform-dependent path separators)
    VIOLATION: Compatibility (Assumes specific OS for file operations)
    VIOLATION: Security (Unsafe YAML deserialization)
    """
    # Hardcoded Windows-style path in cross-platform code
    default_path = "C:\\Program Files\\MyApp\\config.yaml"

    if config_source is None:
        config_source = default_path

    with open(config_source, 'r') as f:
        # VIOLATION: Security (yaml.load without SafeLoader allows arbitrary code execution)
        config = yaml.load(f, Loader=yaml.FullLoader)  # FullLoader is also unsafe in older PyYAML

    # VIOLATION: Compatibility (Locale-dependent string operations)
    if config.get("region", "").upper() == "ISTANBUL":
        # In Turkish locale, "i".upper() != "I", it's "İ"
        pass

    return config


def send_data_to_partner(data):
    """
    VIOLATION: Compatibility (Encoding assumptions)
    VIOLATION: Interoperability (Non-standard date format)
    """
    # Assumes ASCII encoding, will crash on unicode
    encoded = data.encode('ascii')

    # Non-ISO 8601 date format breaks interoperability
    timestamp = time.strftime("%d/%m/%Y %I:%M %p")

    payload = f"{timestamp}|{encoded}"
    return payload


# ============================================================================
# 4. INTERACTION CAPABILITY (Usability) VIOLATIONS
# ============================================================================

class UserInterface:
    """
    VIOLATION: Interaction Capability (No input feedback, cryptic errors)
    """

    def authenticate(self, username, password):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # VIOLATION: Interaction Capability (Same error for all auth failures — good for security
        # but BAD: the error message is cryptic and unhelpful)
        # VIOLATION: Security (SQL Injection)
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()

        if not user:
            # VIOLATION: Interaction Capability (Error code with no explanation)
            return {"error": "E-4019-X", "status": -1}

        # VIOLATION: Security (Returns entire user row including password hash to client)
        return {"user": user, "status": 1}

    def display_progress(self, items):
        """VIOLATION: Interaction Capability (No progress indication for long operation)"""
        results = []
        for item in items:  # Could be millions of items, no feedback
            results.append(self._heavy_computation(item))
        return results

    def _heavy_computation(self, item):
        time.sleep(0.01)
        return item ** 2


# ============================================================================
# 5. RELIABILITY VIOLATIONS
# ============================================================================

def resilient_database_operation(query, params=None):
    """
    VIOLATION: Reliability (Infinite retry with no backoff, no circuit breaker)
    VIOLATION: Reliability (Catches all exceptions indiscriminately)
    """
    global _last_error
    while True:  # Infinite retry loop
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            result = cursor.fetchall()
            # VIOLATION: Reliability (Connection never closed on success path... wait, it is below)
            # Actually: connection closed but result fetched AFTER commit
            conn.close()
            return result
        except Exception as e:
            # VIOLATION: Reliability (Swallows ALL exceptions including KeyboardInterrupt)
            _last_error = str(e)
            logger.debug(f"Retrying query: {query} with error: {e}")
            # No sleep, no backoff — will hammer the database
            continue


def cleanup_temp_files(directory):
    """
    VIOLATION: Reliability (Race condition in file cleanup — TOCTOU)
    VIOLATION: Security (Path traversal not validated)
    """
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        # TOCTOU: file could be deleted between isfile check and remove
        if os.path.isfile(filepath):
            if filename.endswith(".tmp"):
                os.remove(filepath)  # Could raise if already deleted


class ConnectionPool:
    """
    VIOLATION: Reliability (Resource leak — connections never returned to pool)
    VIOLATION: Reliability (Thread-unsafe without locks)
    """

    def __init__(self, size=10):
        self._pool = [sqlite3.connect(DB_PATH) for _ in range(size)]
        self._in_use = []

    def acquire(self):
        if self._pool:
            conn = self._pool.pop()
            self._in_use.append(conn)
            return conn
        # VIOLATION: Reliability (Returns None instead of raising/blocking)
        return None

    def release(self, conn):
        # VIOLATION: Bug — checks wrong list, connection never actually returned
        if conn in self._pool:  # Should check self._in_use
            self._pool.append(conn)
            self._in_use.remove(conn)


# ============================================================================
# 6. SECURITY VIOLATIONS
# ============================================================================

def process_data(user_input_id, raw_payload, config_options):
    """
    Original function with additional subtle vulnerabilities.
    """
    global _global_user_cache, _request_counter
    _request_counter += 1  # VIOLATION: Thread-unsafe increment

    # VIOLATION: Security (SQL Injection via string concatenation)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + str(user_input_id)
    cursor.execute(query)
    user = cursor.fetchone()

    if user:
        # VIOLATION: Security (Storing sensitive data in global mutable dict)
        _global_user_cache[user_input_id] = user

        if config_options:
            for option in config_options:
                if option == 'encrypt':
                    # VIOLATION: Security (MD5 is cryptographically broken)
                    for i in range(1000):
                        hashed_payload = hashlib.md5(raw_payload.encode()).hexdigest()
                elif option == 'backup':
                    # VIOLATION: Security (Command Injection)
                    os.system(f"cp {DB_PATH} backup_{user_input_id}.db")
                elif option == 'export':
                    # VIOLATION: Security (SSRF — fetches arbitrary URL from user input)
                    _export_data(user_input_id)
                elif option == 'transform':
                    # VIOLATION: Security (XML External Entity injection)
                    _parse_xml_payload(raw_payload)
                else:
                    x = 10
                    y = 20
                    z = x + y
                    pass
        else:
            print("No options")
    else:
        try:
            1 / 0
        except:
            pass

    # VIOLATION: Performance Efficiency (O(n²) where O(n) suffices)
    list_a = list(range(10000))
    list_b = list(range(10000))
    duplicates = []
    for a in list_a:
        for b in list_b:
            if a == b:
                duplicates.append(a)

    # VIOLATION: Security (Sensitive data in logs)
    logger.info(f"User {user} processed with key {SECRET_KEY}, token {API_TOKEN}")
    print(f"DEBUG: User {user} processed with key {SECRET_KEY}")

    process_complex_logic_part_2(raw_payload)
    _process_user_template(user_input_id, raw_payload)

    return True


def _export_data(user_input):
    """
    VIOLATION: Security (Server-Side Request Forgery — SSRF)
    Fetches a URL constructed from user input without validation.
    """
    # User could pass "http://169.254.169.254/latest/meta-data/" to access AWS metadata
    url = f"http://internal-api.company.com/export/{user_input}"
    try:
        response = urlopen(url, timeout=5)
        return response.read()
    except Exception:
        pass


def _parse_xml_payload(xml_string):
    """
    VIOLATION: Security (XXE — XML External Entity Injection)
    Default ElementTree in some configurations resolves external entities.
    """
    # Attacker could include <!ENTITY xxe SYSTEM "file:///etc/passwd">
    tree = ET.fromstring(xml_string)
    return tree


def _process_user_template(user_id, template_string):
    """
    VIOLATION: Security (Server-Side Template Injection via format_map)
    Subtle: format_map with user-controlled input allows attribute access.
    """

    class TemplateContext:
        def __init__(self):
            self.user_id = user_id
            self.secret = SECRET_KEY
            self.config = {"db_password": DB_PASSWORD}

    ctx = TemplateContext()
    # User can inject {secret} or {config[db_password]} to extract secrets
    try:
        result = template_string.format_map(vars(ctx))
    except (KeyError, AttributeError):
        result = template_string
    return result


def process_complex_logic_part_2(data):
    """
    VIOLATION: Security (Arbitrary Code Execution via eval)
    VIOLATION: Security (Arbitrary Code Execution via pickle)
    """
    try:
        decoded_data = base64.b64decode(data)
        # VIOLATION: Security (eval on untrusted input)
        result = eval(decoded_data)
    except Exception as e:
        # VIOLATION: Reliability (Stack trace / internal info in error message)
        print(f"System Error in Module X-99 at Memory Address 0x004: {e}")

    # VIOLATION: Security (Unsafe deserialization — pickle allows arbitrary code execution)
    try:
        obj = pickle.loads(base64.b64decode(data))
    except Exception:
        pass


def create_user(username, password, role="user"):
    """
    VIOLATION: Security (Password stored in plaintext)
    VIOLATION: Security (No password policy enforcement)
    VIOLATION: Security (Mass assignment — role parameter directly from input)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # VIOLATION: Security (Password stored as plaintext)
    cursor.execute(
        f"INSERT INTO users (username, password, role) VALUES ('{username}', '{password}', '{role}')"
    )
    conn.commit()
    conn.close()

    # VIOLATION: Security (Logging plaintext password)
    logger.info(f"Created user {username} with password {password} and role {role}")
    return True


def verify_token(token):
    """
    VIOLATION: Security (Timing attack vulnerability in token comparison)
    VIOLATION: Security (Weak token generation)
    """
    # VIOLATION: Security (Token generated from predictable source)
    expected = hashlib.md5((JWT_SECRET + str(int(time.time()) // 300)).encode()).hexdigest()

    # VIOLATION: Security (String comparison vulnerable to timing attack)
    # Early-exit comparison leaks token length and character values through timing
    if len(token) != len(expected):
        return False
    for a, b in zip(token, expected):
        if a != b:
            return False
    return True


def generate_session_id():
    """
    VIOLATION: Security (Predictable session ID using weak PRNG)
    """
    # random.random() uses Mersenne Twister — predictable after 624 observations
    random.seed(int(time.time()))  # Seed from current time makes it even more predictable
    return hashlib.md5(str(random.random()).encode()).hexdigest()


def execute_user_plugin(plugin_code):
    """
    VIOLATION: Security (Arbitrary code execution via compile + exec)
    Subtle because it uses compile() first which might look like "validation"
    """
    try:
        # compile() does NOT sandbox — it just parses. exec() runs arbitrary code.
        compiled = compile(plugin_code, "<user_plugin>", "exec")
        exec(compiled, {"__builtins__": __builtins__})  # Full builtins access
    except SyntaxError:
        pass


def load_user_module(module_path):
    """
    VIOLATION: Security (Arbitrary module loading from user-controlled path)
    """
    spec = importlib.util.spec_from_file_location("user_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # Executes arbitrary Python file
    return module


def check_access(user_role, required_role):
    """
    VIOLATION: Security (Broken access control — logic inversion)
    Subtle: the function name suggests it checks access, but the logic is inverted.
    """
    # This SHOULD return True when user has sufficient privileges
    # BUG: Returns True when user DOESN'T have the role (logic inverted)
    role_hierarchy = {"admin": 3, "manager": 2, "user": 1, "guest": 0}
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    # Subtle inversion: < instead of >=
    return user_level < required_level


def sanitize_html(user_input):
    """
    VIOLATION: Security (Incomplete XSS sanitization — regex bypass)
    Looks like it sanitizes but can be trivially bypassed.
    """
    # Only removes <script> tags, misses event handlers, SVG, etc.
    # Also case-sensitive, so <SCRIPT> or <ScRiPt> bypasses it
    sanitized = re.sub(r'<script.*?>.*?</script>', '', user_input)
    # Does not handle: <img onerror=alert(1)>, <svg onload=...>, javascript: URIs
    return sanitized


def validate_redirect_url(url):
    """
    VIOLATION: Security (Open redirect — insufficient URL validation)
    Subtle: checks startswith which can be bypassed with evil.com?http://safe.com
    """
    allowed_hosts = ["https://app.company.com", "https://www.company.com"]

    for host in allowed_hosts:
        if url.startswith(host):
            return url  # Bypassed with: https://app.company.com.evil.com/phish

    # Falls through to return the URL anyway — missing denial
    return url  # VIOLATION: Should return a safe default, not the potentially malicious URL


# ============================================================================
# 7. MAINTAINABILITY VIOLATIONS
# ============================================================================

def x(p1, p2):
    """VIOLATION: Maintainability (Meaningless function/variable names)"""
    return p1 * p2


def x2(p1, p2):
    """VIOLATION: Maintainability (Duplicate function with slightly different name)"""
    return p1 * p2


def process_order_calculate_tax_send_email_update_inventory_log_audit(
        order_id, user_id, items, payment_info, shipping_address,
        promo_code, gift_wrap, notification_preferences, referral_code,
        loyalty_points, insurance_option, delivery_instructions
):
    """
    VIOLATION: Maintainability (God function — does everything in one place)
    VIOLATION: Maintainability (Too many parameters)
    VIOLATION: Maintainability (Function name describes multiple responsibilities)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # "Calculate" tax
    total = 0
    for item in items:
        # VIOLATION: Maintainability (Magic numbers)
        if item['category'] == 1:
            total += item['price'] * 1.07
        elif item['category'] == 2:
            total += item['price'] * 1.12
        elif item['category'] == 3:
            total += item['price'] * 1.0
        elif item['category'] == 4:
            total += item['price'] * 1.15
        elif item['category'] == 5:
            total += item['price'] * 1.22
        elif item['category'] == 6:
            total += item['price'] * 1.18
        elif item['category'] == 7:
            total += item['price'] * 1.05
        elif item['category'] == 8:
            total += item['price'] * 1.09
        # Categories 9+ silently have no tax — a functional bug

    # Apply promo
    if promo_code == "SAVE10":
        total *= 0.9
    elif promo_code == "SAVE20":
        total *= 0.8
    elif promo_code == "SAVE50":
        total *= 0.5
    elif promo_code == "FREE":
        total = 0  # VIOLATION: Functional (Anyone can get free orders with this code)

    # Loyalty points — wrong conversion
    if loyalty_points:
        total -= loyalty_points * 0.001  # Should be 0.01, off by factor of 10

    # "Send email" by printing
    print(f"EMAIL TO {user_id}: Your order {order_id} total is {total}")

    # "Update inventory"
    for item in items:
        cursor.execute(
            f"UPDATE inventory SET stock = stock - {item['quantity']} "
            f"WHERE product_id = {item['id']}"
        )
        # VIOLATION: No check if stock goes negative

    # "Log audit"
    cursor.execute(
        f"INSERT INTO audit_log VALUES ('{order_id}', '{user_id}', "
        f"'{payment_info}', '{total}', '{time.time()}')"
    )
    # VIOLATION: Security (Full payment info including card numbers in audit log)

    conn.commit()
    conn.close()
    return total


class DataProcessor:
    """
    VIOLATION: Maintainability (God class — handles unrelated concerns)
    """

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.cache = {}
        self.logger = logging.getLogger("processor")
        self._temp_files = []

    def process(self, data):
        return self._step1(data)

    def _step1(self, data):
        return self._step2(data)

    def _step2(self, data):
        return self._step3(data)

    def _step3(self, data):
        return self._step4(data)

    def _step4(self, data):
        return self._step5(data)

    def _step5(self, data):
        """VIOLATION: Maintainability (Deep call chain, hard to debug/trace)"""
        return data

    def __del__(self):
        """
        VIOLATION: Reliability (Destructor-based cleanup is unreliable in Python)
        The GC may never call __del__, leaking the connection.
        """
        try:
            self.conn.close()
        except:
            pass

    # VIOLATION: Maintainability (Copy-pasted code with minor variation)
    def process_type_a(self, data):
        result = []
        for item in data:
            if item.get('type') == 'A':
                transformed = item['value'] * 2 + 10
                result.append(transformed)
        return result

    def process_type_b(self, data):
        result = []
        for item in data:
            if item.get('type') == 'B':
                transformed = item['value'] * 2 + 10  # Identical logic!
                result.append(transformed)
        return result

    def process_type_c(self, data):
        result = []
        for item in data:
            if item.get('type') == 'C':
                transformed = item['value'] * 2 + 10  # Same again!
                result.append(transformed)
        return result


# ============================================================================
# 8. SAFETY & PORTABILITY VIOLATIONS
# ============================================================================

def write_to_shared_memory(data):
    """
    VIOLATION: Safety (Unsafe memory manipulation without bounds checking)
    VIOLATION: Portability (mmap behavior differs across OS)
    """
    size = len(data)
    # Create anonymous memory map
    mm = mmap.mmap(-1, size)
    mm.write(data)
    # VIOLATION: Safety (No cleanup — mmap never closed)
    # VIOLATION: Safety (Buffer can be read by other processes)
    return mm


def call_native_function(lib_path, func_name, *args):
    """
    VIOLATION: Safety (Loading arbitrary native library)
    VIOLATION: Safety (No type checking on ctypes arguments)
    VIOLATION: Portability (Assumes specific ABI)
    """
    lib = ctypes.CDLL(lib_path)
    func = getattr(lib, func_name)
    # Calling C function with no type safety — can cause segfault / memory corruption
    return func(*args)


def unsafe_signal_handler():
    """
    VIOLATION: Safety (Non-reentrant operations in signal handler)
    VIOLATION: Reliability (Signal handler modifies global state)
    """
    global _global_user_cache

    def handler(signum, frame):
        # VIOLATION: Doing I/O and lock-requiring operations in signal handler is unsafe
        logger.info(f"Received signal {signum}")
        _global_user_cache.clear()
        conn = sqlite3.connect(DB_PATH)  # NOT async-signal-safe
        conn.execute("INSERT INTO events VALUES ('shutdown', datetime('now'))")
        conn.commit()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


# ============================================================================
# 9. CONCURRENCY VIOLATIONS
# ============================================================================

class UnsafeCounter:
    """
    VIOLATION: Reliability (Race condition — no synchronization)
    Subtle: looks like a simple counter but is completely broken under threading.
    """

    def __init__(self):
        self.count = 0
        self._history = []

    def increment(self):
        # VIOLATION: Read-modify-write without lock
        current = self.count
        time.sleep(0.0001)  # Widens the race window
        self.count = current + 1
        self._history.append(self.count)

    def get_count(self):
        return self.count


_shared_counter = UnsafeCounter()


def worker_thread(iterations):
    """Demonstrates the race condition in UnsafeCounter."""
    for _ in range(iterations):
        _shared_counter.increment()


class BackgroundService(threading.Thread):
    """
    VIOLATION: Reliability (Daemon thread with no graceful shutdown)
    VIOLATION: Reliability (Unhandled exception kills thread silently)
    """

    def __init__(self):
        super().__init__(daemon=True)  # Daemon=True means it dies with main thread
        self.running = True

    def run(self):
        while self.running:
            # VIOLATION: No try/except — any exception kills the thread silently
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE expiry < ?", (time.time(),))
            conn.commit()
            conn.close()
            time.sleep(60)
            # VIOLATION: If DB is locked, thread crashes with no recovery


# ============================================================================
# 10. NETWORK & SERVER VIOLATIONS
# ============================================================================

class VulnerableHandler(BaseHTTPRequestHandler):
    """
    VIOLATION: Security (HTTP server with multiple vulnerabilities)
    """

    def do_GET(self):
        # VIOLATION: Security (Path traversal)
        filepath = os.path.join("/var/www", self.path.lstrip("/"))
        # Attacker sends: GET /../../../etc/passwd
        # os.path.join doesn't prevent traversal when path contains ..

        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            # VIOLATION: Security (Full path disclosure in error)
            self.wfile.write(f"File not found: {filepath}".encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        # VIOLATION: Security (Deserializing user-provided data with marshal)
        # marshal.loads can execute arbitrary code similar to pickle
        try:
            data = marshal.loads(body)
        except Exception:
            # VIOLATION: Security (Falls back to eval)
            data = eval(body.decode())

        self.send_response(200)
        self.end_headers()
        self.wfile.write(str(data).encode())

    def log_message(self, format, *args):
        # VIOLATION: Security (Access logs contain full request including auth headers)
        logger.info(f"{self.client_address} - {self.headers} - {format % args}")


def start_server(port=8080):
    """
    VIOLATION: Security (HTTP server with no TLS)
    VIOLATION: Security (Binds to all interfaces)
    VIOLATION: Reliability (No request size limits — DoS vector)
    """
    server = HTTPServer(("0.0.0.0", port), VulnerableHandler)
    server.serve_forever()


# ============================================================================
# 11. FILE & TEMP FILE VIOLATIONS
# ============================================================================

def create_temp_config(user_data):
    """
    VIOLATION: Security (Predictable temp file name — symlink attack)
    VIOLATION: Security (World-readable permissions)
    """
    # Predictable filename allows symlink attack
    temp_path = f"/tmp/config_{os.getpid()}.json"

    # VIOLATION: Security (Race condition between check and create)
    if not os.path.exists(temp_path):
        with open(temp_path, 'w') as f:
            # VIOLATION: Security (Sensitive data written to world-readable temp file)
            f.write(f'{{"user": "{user_data}", "key": "{SECRET_KEY}"}}')

    return temp_path


def process_uploaded_file(filename, content):
    """
    VIOLATION: Security (Arbitrary file write — path traversal via filename)
    VIOLATION: Security (No file type validation)
    """
    # User could pass filename = "../../etc/cron.d/evil" to write arbitrary cron jobs
    upload_dir = "/var/uploads"
    full_path = os.path.join(upload_dir, filename)  # Path traversal not prevented

    with open(full_path, 'wb') as f:
        f.write(content)

    # VIOLATION: Security (Makes uploaded file executable)
    os.chmod(full_path, 0o777)

    return full_path


# ============================================================================
# 12. ADDITIONAL SUBTLE VIOLATIONS
# ============================================================================

def compare_passwords(stored_hash, user_password):
    """
    VIOLATION: Security (Timing side-channel in password comparison)
    Looks correct but early-exit string comparison leaks info.
    """
    computed_hash = hashlib.sha256(user_password.encode()).hexdigest()
    # Should use hmac.compare_digest() for constant-time comparison
    return computed_hash == stored_hash  # Python == on strings is NOT constant-time


def rate_limiter(client_ip):
    """
    VIOLATION: Security (Race condition in rate limiting — can be bypassed)
    VIOLATION: Security (In-memory only — reset on restart)
    """
    global _global_user_cache

    key = f"rate_{client_ip}"
    current = _global_user_cache.get(key, 0)

    # TOCTOU: between get and set, another thread could also pass the check
    if current > 100:
        return False

    _global_user_cache[key] = current + 1
    return True


def encrypt_sensitive_data(plaintext):
    """
    VIOLATION: Security (ECB mode encryption — patterns preserved)
    VIOLATION: Security (Hardcoded IV of all zeros)
    VIOLATION: Security (Key derived from constant)
    """
    from hashlib import sha256

    # "Derive" key from hardcoded secret (pointless key derivation)
    key = sha256(SECRET_KEY.encode()).digest()[:16]

    # "Encrypt" using XOR with repeating key — not real encryption
    encrypted = bytearray()
    for i, char in enumerate(plaintext.encode()):
        encrypted.append(char ^ key[i % len(key)])

    return base64.b64encode(bytes(encrypted)).decode()


def decrypt_sensitive_data(ciphertext):
    """
    VIOLATION: Security (Reversible "encryption" that's just XOR)
    """
    from hashlib import sha256
    key = sha256(SECRET_KEY.encode()).digest()[:16]

    data = base64.b64decode(ciphertext)
    decrypted = bytearray()
    for i, byte in enumerate(data):
        decrypted.append(byte ^ key[i % len(key)])

    return decrypted.decode()


class InsecureRandom:
    """
    VIOLATION: Security (Custom PRNG for security purposes — predictable)
    Subtle: implements a Linear Congruential Generator that looks random but is fully predictable.
    """

    def __init__(self, seed=None):
        self._state = seed or int(time.time())

    def next(self):
        # LCG with known parameters — trivially predictable
        self._state = (self._state * 1103515245 + 12345) & 0x7FFFFFFF
        return self._state

    def generate_token(self, length=32):
        """Generates a 'random' token that is actually deterministic."""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(chars[self.next() % len(chars)] for _ in range(length))


# VIOLATION: Security (Using insecure random for security-critical token generation)
_token_generator = InsecureRandom()


def generate_password_reset_token(user_id):
    """Generates a predictable password reset token."""
    token = _token_generator.generate_token(32)
    # VIOLATION: Security (Token stored unhashed — if DB is leaked, tokens are usable)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        f"INSERT INTO password_resets VALUES ('{user_id}', '{token}', {time.time() + 3600})"
    )
    conn.commit()
    conn.close()
    return token


# ============================================================================
# 13. TYPE CONFUSION & LOGIC BOMBS
# ============================================================================

def process_payment(amount, currency="USD"):
    """
    VIOLATION: Reliability (Type confusion — no type validation)
    VIOLATION: Functional Suitability (Integer overflow with large amounts)
    """
    # No validation: amount could be string, negative, None, float('inf'), float('nan')
    if currency == "JPY":
        # Japanese Yen has no decimal places, but this code doesn't handle that
        processed_amount = round(amount, 2)  # Wrong for JPY
    else:
        processed_amount = amount

    # VIOLATION: Functional (Negative amounts allow reverse charges / money extraction)
    # No check for amount > 0

    # VIOLATION: Reliability (NaN propagation — NaN comparisons always return False)
    if processed_amount > 10000:
        # Requires approval, but NaN > 10000 is False, so NaN amounts skip approval
        require_approval(processed_amount)

    return {"status": "processed", "amount": processed_amount}


def require_approval(amount):
    """Placeholder — in reality would trigger an approval workflow."""
    logger.info(f"Approval required for amount: {amount}")


def check_maintenance_window():
    """
    VIOLATION: Maintainability (Time bomb — code behaves differently based on date)
    VIOLATION: Reliability (Hidden conditional behavior)
    """
    import datetime
    now = datetime.datetime.now()

    # Subtle: this disables ALL security checks on weekends
    if now.weekday() >= 5:
        return True  # "Maintenance mode" — bypasses auth

    # And on the first of any month
    if now.day == 1:
        return True

    return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # VIOLATION: Safety (No graceful shutdown handler)
    unsafe_signal_handler()

    # VIOLATION: Functional Suitability (Running exploit payload as test)
    process_data("1 OR 1=1 --", "cHJpbnQoJ2hhY2tlZCcp", ['encrypt', 'backup', 'export'])

    # VIOLATION: Concurrency (Unsynchronized threads modifying shared state)
    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker_thread, args=(1000,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Expected: 10000, Actual: significantly less due to race condition
    print(f"Counter value (expected 10000): {_shared_counter.get_count()}")

    # VIOLATION: Performance (Materializes 10M items just to print count)
    ids = generate_report_ids()
    print(f"Generated {len(ids)} report IDs")

    # Start insecure HTTP server
    print("Starting server on 0.0.0.0:8080 (HTTP, no TLS)...")
    start_server()
