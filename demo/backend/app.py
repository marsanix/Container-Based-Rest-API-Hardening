import os
import time
import pymysql
import base64
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

app = Flask(__name__)

# Config DB
DB_HOST = os.getenv("DB_HOST", "10.10.10.60")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rahasia")
DB_NAME = os.getenv("DB_NAME", "karyawan_db")

# Load AES Key (16 bytes for AES-128)
key_hex = os.getenv("APP_ENCRYPTION_KEY", "11223344556677889900aabbccddeeff")
try:
    aes_key = bytes.fromhex(key_hex)
    aesgcm = AESGCM(aes_key)
except Exception as e:
    aesgcm = None
    print(f"Failed to load AES key: {e}")

db_initialized = False

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS employees (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        position VARCHAR(255) NOT NULL,
                        salary_encrypted VARCHAR(255) NOT NULL
                    )
                ''')
            conn.commit()
            conn.close()
            print("Database initialized successfully.")
            return True
        except Exception as e:
            print(f"Waiting for database... ({e})")
            retries -= 1
            time.sleep(2)
    return False

@app.before_request
def setup_db():
    global db_initialized
    if not db_initialized:
        # Pengecualian path root agar health check load balancer tidak tersangkut
        if request.path != "/":
            if init_db():
                db_initialized = True

# --- ENCRYPTION LOGIC (AES-128-GCM) ---
def encrypt_salary(salary_str):
    if not aesgcm:
        return ""
    # Best Practice: Generate 12-byte random nonce for GCM
    nonce = os.urandom(12)
    # Encrypts and appends MAC tag automatically
    ciphertext = aesgcm.encrypt(nonce, salary_str.encode('utf-8'), None)
    # Store nonce + ciphertext together, encoded in Base64
    return base64.b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_salary(encrypted_b64):
    if not aesgcm or not encrypted_b64:
        return "[Error]"
    try:
        data = base64.b64decode(encrypted_b64.encode('utf-8'))
        nonce, ciphertext = data[:12], data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
    except Exception as e:
        return f"[Decryption Failed]"

# --- ENDPOINTS ---

@app.route("/api/login", methods=["POST"])
def login():
    """Endpoint dipertahankan untuk kompatibilitas pengujian Skenario A (Sniffing HTTP POST)"""
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if username == "admin" and password == "rahasia123":
        return jsonify({"status": "success", "message": "Autentikasi berhasil", "token": "DEMO_TOKEN"}), 200
    else:
        return jsonify({"status": "failed", "message": "Kredensial tidak valid"}), 401

@app.route("/api/employees", methods=["GET"])
def get_employees():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM employees")
            rows = cursor.fetchall()
            for row in rows:
                row['salary'] = decrypt_salary(row['salary_encrypted'])
                row['salary_encrypted'] = "HIDDEN" # Jangan kirim ciphertext ke frontend untuk demo ini
        conn.close()
        return jsonify({"status": "success", "data": rows}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/employees", methods=["POST"])
def create_employee():
    data = request.get_json() or {}
    name = data.get("name")
    position = data.get("position")
    salary = data.get("salary")
    
    if not name or not position or not salary:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    # Lakukan enkripsi AES-128-GCM di layer aplikasi sebelum ke database
    salary_encrypted = encrypt_salary(str(salary))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO employees (name, position, salary_encrypted) VALUES (%s, %s, %s)",
                (name, position, salary_encrypted)
            )
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Employee created"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM employees WHERE id = %s", (emp_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Employee deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "service": "Backend API"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
