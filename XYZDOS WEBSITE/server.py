"""
XYZDOS Website Server
- Serves the landing page
- Logs every visitor (IP, time, user-agent, page)
- Admin login panel to view visitor logs

Requirements: pip install flask
"""

from flask import Flask, request, jsonify, session, send_from_directory
import json
import os
import threading
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.environ.get('FLASK_SECRET', 'xyzdos-admin-secret-key-change-me')

# --- Config ---
# Set ADMIN_PASS environment variable, or default to admin123
ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'XYZDOSADMIN')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'IHEARTDDOS')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'visitors.json')
HTML_FILE = 'index.html'
_write_lock = threading.Lock()

# --- Helpers ---
def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_logs(logs):
    with _write_lock:
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# --- Routes ---

@app.route('/')
def serve_index():
    return send_from_directory('.', HTML_FILE)

@app.route('/api/log-visit', methods=['POST'])
def log_visit():
    """Log a visitor's IP, time, and user-agent."""
    data = request.get_json(silent=True) or {}
    
    # Get IP - handle proxies
    ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown')
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    
    visit = {
        "ip": ip,
        "time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "user_agent": request.headers.get('User-Agent', 'unknown'),
        "referer": data.get('referer', ''),
        "page": data.get('page', '/')
    }
    
    logs = load_logs()
    logs.append(visit)
    
    # Keep max 10000 entries
    if len(logs) > 10000:
        logs = logs[-10000:]
    
    save_logs(logs)
    
    return jsonify({"status": "logged"})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Log in to the admin panel."""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({"status": "ok"})
    
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({"status": "ok"})

@app.route('/api/admin/visits', methods=['GET'])
@login_required
def get_visits():
    """Get all visitor logs (admin only)."""
    logs = load_logs()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search_ip = request.args.get('search', '').strip()
    
    if search_ip:
        logs = [v for v in logs if search_ip in v.get('ip', '')]
    
    total = len(logs)
    start = (page - 1) * per_page
    end = start + per_page
    page_logs = logs[start:end] if start < total else []
    
    unique_ips = len(set(v.get('ip', '') for v in logs))
    
    return jsonify({
        "visits": page_logs,
        "total": total,
        "unique_ips": unique_ips,
        "page": page,
        "per_page": per_page
    })

@app.route('/api/admin/stats', methods=['GET'])
@login_required
def get_stats():
    """Get summary stats (admin only)."""
    logs = load_logs()
    
    unique_ips = len(set(v.get('ip', '') for v in logs))
    today = datetime.utcnow().strftime('%Y-%m-%d')
    today_count = sum(1 for v in logs if v.get('time', '').startswith(today))
    
    return jsonify({
        "total_visits": len(logs),
        "unique_ips": unique_ips,
        "today_visits": today_count
    })

# Catch-all static file route MUST be last
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    pass_warning = " ⚠️  DEFAULT CREDENTIALS - SET ENV VARS!" if ADMIN_PASSWORD == 'IHEARTDDOS' else ""
    print("╔══════════════════════════════════════════╗")
    print("║        XYZDOS Website Server v1.0        ║")
    print("╠══════════════════════════════════════════╣")
    print(f"║  Port:   {port}                              ║")
    print(f"║  User:   {ADMIN_USERNAME}                      ║")
    print(f"║  Pass:   {ADMIN_PASSWORD}                      ║")
    if pass_warning:
        print(f"║{pass_warning}║")
    print("╚══════════════════════════════════════════╝")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
