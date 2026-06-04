from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import time
import random
import string
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_fallback')

# Firebase Initialization
if not firebase_admin._apps:
    cred_json = os.environ.get('FIREBASE_CREDS_JSON')
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print("Failed to initialize Firebase with FIREBASE_CREDS_JSON:", e)
    else:
        try:
            firebase_admin.initialize_app()
        except Exception as e:
            print("Failed to initialize default Firebase app:", e)

# Only initialize db if firebase was successfully initialized
try:
    db = firestore.client()
except Exception:
    db = None

# ==========================================
# INITIALIZATION
# ==========================================

def get_setting(key, default):
    if not db: return default
    try:
        doc = db.collection('settings').document(key).get()
        if doc.exists:
            return doc.to_dict().get('value', default)
    except Exception:
        pass
    return default

def set_setting(key, value):
    if not db: return
    db.collection('settings').document(key).set({'value': str(value)})

if db:
    try:
        if get_setting('status', None) is None:
            set_setting('status', 'Draft')
            set_setting('title', 'Official Government Election 2026')
            set_setting('description', 'Please cast your vote carefully. This ballot is securely encrypted.')
            set_setting('choice_rule', 'Single Choice')
            set_setting('logo', '🏛️')
    except Exception as e:
        print("Settings initialization failed:", e)

def generate_pin():
    chars = string.ascii_uppercase + string.digits
    for c in ['O', '0', 'I', '1']: chars = chars.replace(c, '')
    return ''.join(random.choice(chars) for _ in range(6))

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    if not db: return "Firebase Database not configured. Please set FIREBASE_CREDS_JSON.", 500
    candidates_ref = db.collection('candidates').stream()
    candidates = [{'id': c.id, **c.to_dict()} for c in candidates_ref]
    status = get_setting('status', 'Draft')
    
    tally = []
    if status == 'Closed':
        for c in candidates:
            # Note: For large elections, counting votes like this is inefficient, but okay for this scale
            votes = list(db.collection('votes').where('candidate_id', '==', c['id']).stream())
            tally.append({'name': c['name'], 'count': len(votes)})
            
    return render_template('public_dashboard.html', candidates=candidates, status=status, tally=tally)

@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if not db: return "Firebase Database not configured.", 500
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        pin = request.form.get('pin', '').strip()
        
        if get_setting('status', 'Draft') != 'Active':
            flash("Error: The election is not currently active.", "danger")
            return redirect(url_for('voter_login'))
            
        voter_query = list(db.collection('voters').where('email', '==', email).where('pin', '==', pin).limit(1).stream())
        
        if voter_query:
            voter_doc = voter_query[0]
            voter_data = voter_doc.to_dict()
            if voter_data.get('has_voted'):
                flash("Error: This PIN has already been used to cast a ballot.", "danger")
            else:
                session['voter_id'] = voter_doc.id
                session['voter_name'] = voter_data.get('name')
                return redirect(url_for('voter_ballot'))
        else:
            flash("Error: Invalid credentials.", "danger")
            
    return render_template('voter_login.html')

@app.route('/voter/ballot', methods=['GET', 'POST'])
def voter_ballot():
    if not db: return "Firebase Database not configured.", 500
    if 'voter_id' not in session: return redirect(url_for('voter_login'))
        
    if get_setting('status', 'Draft') != 'Active':
        session.clear()
        flash("Election is no longer active.", "danger")
        return redirect(url_for('voter_login'))
        
    voter_ref = db.collection('voters').document(session['voter_id'])
    voter_doc = voter_ref.get()
    
    if not voter_doc.exists or voter_doc.to_dict().get('has_voted'):
        session.clear()
        return redirect(url_for('voter_login'))
        
    candidates_ref = db.collection('candidates').stream()
    candidates = [{'id': c.id, **c.to_dict()} for c in candidates_ref]
    
    if request.method == 'POST':
        selections = request.form.getlist('candidate_id')
        if not selections:
            flash("Please select at least one candidate.", "danger")
            return redirect(url_for('voter_ballot'))
            
        if get_setting('choice_rule', 'Single Choice') == 'Single Choice' and len(selections) > 1:
            flash("You can only select one candidate.", "danger")
            return redirect(url_for('voter_ballot'))
            
        # Cast vote secretly
        for c_id in selections:
            db.collection('votes').add({
                'candidate_id': c_id,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
        voter_ref.update({'has_voted': True})
        
        session.clear()
        return render_template('success.html')
        
    return render_template('ballot.html', 
                           candidates=candidates, 
                           title=get_setting('title', ''), 
                           desc=get_setting('description', ''),
                           logo=get_setting('logo', ''),
                           rule=get_setting('choice_rule', ''),
                           voter_name=session['voter_name'])

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if request.form.get('username') == admin_username and request.form.get('password') == admin_password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid Global Admin credentials.", "danger")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    if not db: return "Firebase Database not configured.", 500
    
    candidates_ref = db.collection('candidates').stream()
    candidates = [{'id': c.id, **c.to_dict()} for c in candidates_ref]
    
    voters_ref = db.collection('voters').stream()
    voters = [{'id': v.id, **v.to_dict()} for v in voters_ref]
    
    status = get_setting('status', 'Draft')
    
    # In a real large-scale app, counting all votes requires aggregation. 
    # For this portal, pulling all votes is acceptable.
    votes_ref = list(db.collection('votes').stream())
    turnout = len(votes_ref)
    total = len(voters)
    pct = int((turnout / total) * 100) if total > 0 else 0
    
    tally = []
    for c in candidates:
        votes_for_c = len([v for v in votes_ref if v.to_dict().get('candidate_id') == c['id']])
        tally.append({'name': c['name'], 'count': votes_for_c})
    
    return render_template('admin_dashboard.html', 
                           candidates=candidates, 
                           voters=voters, 
                           status=status,
                           turnout=turnout, 
                           total=total, 
                           pct=pct,
                           tally=tally)

@app.route('/admin/api/add_candidate', methods=['POST'])
def api_add_candidate():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        db.collection('candidates').add({
            'name': request.form.get('name'), 
            'party': request.form.get('party', 'Independent'), 
            'bio': request.form.get('bio')
        })
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/add_voter', methods=['POST'])
def api_add_voter():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        email = request.form.get('email').lower().strip()
        existing = list(db.collection('voters').where('email', '==', email).limit(1).stream())
        if existing:
            flash("Email already registered.", "danger")
        else:
            db.collection('voters').add({
                'name': request.form.get('name'), 
                'email': email, 
                'pin': generate_pin(),
                'has_voted': False
            })
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/launch', methods=['POST'])
def api_launch():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    set_setting('status', 'Active')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/close', methods=['POST'])
def api_close():
    if not session.get('admin_logged_in'): return "Unauthorized", 401
    set_setting('status', 'Closed')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/reset', methods=['POST'])
def api_reset():
    if not session.get('admin_logged_in'): return "Unauthorized", 401
    if db:
        # Delete all votes
        votes = db.collection('votes').stream()
        for v in votes: v.reference.delete()
        
        # Reset all voters
        voters = db.collection('voters').stream()
        for v in voters:
            v.reference.update({'has_voted': False, 'pin': generate_pin()})
            
        set_setting('status', 'Draft')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/delete_candidate/<id>', methods=['POST'])
def api_delete_candidate(id):
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        db.collection('candidates').document(id).delete()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/delete_voter/<id>', methods=['POST'])
def api_delete_voter(id):
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        db.collection('voters').document(id).delete()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/clear_candidates', methods=['POST'])
def api_clear_candidates():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        votes = db.collection('votes').stream()
        for v in votes: v.reference.delete()
        
        cands = db.collection('candidates').stream()
        for c in cands: c.reference.delete()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/clear_voters', methods=['POST'])
def api_clear_voters():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    if db:
        voters = db.collection('voters').stream()
        for v in voters: v.reference.delete()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
