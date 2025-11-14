import argparse
from flask import Flask, jsonify, request, abort, session, redirect, url_for
import os
import sys
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.aixn.security.ip_whitelist import IPWhitelist
from src.aixn.security.audit_logger import AuditLogger # Import AuditLogger

app = Flask(__name__)
# IMPORTANT: Replace with a strong, randomly generated secret key in a real application
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_for_dev_only") 

ip_whitelist = IPWhitelist()
audit_logger = AuditLogger() # Initialize AuditLogger

# Initialize Flask-Limiter
# Using an in-memory storage for simplicity. For production, use Redis or Memcached.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"], # Global default limits
    storage_uri="memory://",
    strategy="fixed-window" # or "moving-window"
)

# Placeholder for user authentication (replace with a real user management system)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            audit_logger.log_action(request.remote_addr, "api_access", {"path": request.path}, "FAILURE_UNAUTHORIZED")
            abort(401, description="Unauthorized: Login required.")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return "AIXN Node is running."

@app.route('/login', methods=['POST'])
@ip_whitelist.whitelist_required() # Protect login endpoint with IP whitelist
@limiter.limit("5 per minute", key_func=lambda: session.sid if session.sid else get_remote_address()) # Limit login attempts per session/IP
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    ip_address = request.remote_addr

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        session.permanent = True # Make session last longer
        audit_logger.log_action(username, "login", {"ip_address": ip_address}, "SUCCESS")
        return jsonify({"message": "Logged in successfully."}), 200
    else:
        audit_logger.log_action(username, "login", {"ip_address": ip_address}, "FAILURE_INVALID_CREDENTIALS")
        return jsonify({"message": "Invalid credentials."}), 401

@app.route('/logout')
@login_required
def logout():
    user_id = session.get('username', 'unknown') # Assuming username is stored in session
    session.pop('logged_in', None)
    audit_logger.log_action(user_id, "logout", {"ip_address": request.remote_addr}, "SUCCESS")
    return jsonify({"message": "Logged out successfully."}), 200

@app.route('/admin/status')
@ip_whitelist.whitelist_required()
@login_required
@limiter.limit("10 per minute", key_func=lambda: session.sid) # Limit admin status requests per logged-in session
def admin_status():
    user_id = session.get('username', 'unknown')
    audit_logger.log_action(user_id, "admin_status_check", {"ip_address": request.remote_addr}, "SUCCESS")
    return jsonify({"status": "Admin access granted", "message": "Node is healthy."})

@app.route('/public/data')
@limiter.limit("100 per minute") # Public data can have a higher rate limit
def public_data():
    return jsonify({"data": "This is public data."})

def main():
    parser = argparse.ArgumentParser(description="AIXN Blockchain Node.")
    parser.add_argument("--host", default="127.0.0.1", help="Host address for the node's API.")
    parser.add_argument("--rpc-port", type=int, default=18545, help="RPC/Web API port.")
    
    args = parser.parse_args()

    print(f"Starting AIXN Node API on http://{args.host}:{args.rpc_port}")
    print(f"Admin endpoints are protected by IP Whitelist. Whitelisted IPs: {[str(ip) for ip in ip_whitelist.whitelisted_ips]}")
    app.run(host=args.host, port=args.rpc_port)

if __name__ == "__main__":
    # Ensure the config directory exists for IPWhitelist
    os.makedirs("config", exist_ok=True)
    # Add localhost to the whitelist for testing purposes
    ip_whitelist.add_ip("127.0.0.1")
    main()
