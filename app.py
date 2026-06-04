from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import time
import random
import string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_fallback')

# Live Database configuration
# Uses DATABASE_URL from environment if available
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    if os.environ.get('VERCEL'):
        database_url = 'sqlite:////tmp/live_election.db'
    else:
        database_url = 'sqlite:///live_election.db'
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==========================================
# RELATIONAL DATABASE MODELS
# ==========================================

class ElectionSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)

class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    pin = db.Column(db.String(20), unique=True, nullable=False)
    has_voted = db.Column(db.Boolean, default=False)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    party = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    # No link to Voter to preserve cryptographic secrecy

# ==========================================
# INITIALIZATION
# ==========================================

def get_setting(key, default):
    setting = ElectionSettings.query.filter_by(key=key).first()
    return setting.value if setting else default

def set_setting(key, value):
    setting = ElectionSettings.query.filter_by(key=key).first()
    if setting:
        setting.value = str(value)
    else:
        new_setting = ElectionSettings(key=key, value=str(value))
        db.session.add(new_setting)
    db.session.commit()

db_initialized = False

@app.before_request
def initialize_db():
    global db_initialized
    if not db_initialized:
        db.create_all()
        # Initialize basic settings if they don't exist
        if not ElectionSettings.query.filter_by(key='status').first():
            set_setting('status', 'Draft')
            set_setting('title', 'Official Government Election 2026')
            set_setting('description', 'Please cast your vote carefully. This ballot is securely encrypted.')
            set_setting('choice_rule', 'Single Choice')
            set_setting('logo', '🏛️')
        db_initialized = True

def generate_pin():
    chars = string.ascii_uppercase + string.digits
    for c in ['O', '0', 'I', '1']: chars = chars.replace(c, '')
    return ''.join(random.choice(chars) for _ in range(6))

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    candidates = Candidate.query.all()
    status = get_setting('status', 'Draft')
    
    tally = []
    if status == 'Closed':
        for c in candidates:
            votes_for_c = Vote.query.filter_by(candidate_id=c.id).count()
            tally.append({'name': c.name, 'count': votes_for_c})
            
    return render_template('public_dashboard.html', candidates=candidates, status=status, tally=tally)

@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        pin = request.form.get('pin', '').strip()
        
        if get_setting('status', 'Draft') != 'Active':
            flash("Error: The election is not currently active.", "danger")
            return redirect(url_for('voter_login'))
            
        voter = Voter.query.filter_by(email=email, pin=pin).first()
        
        if voter:
            if voter.has_voted:
                flash("Error: This PIN has already been used to cast a ballot.", "danger")
            else:
                session['voter_id'] = voter.id
                session['voter_name'] = voter.name
                return redirect(url_for('voter_ballot'))
        else:
            flash("Error: Invalid credentials.", "danger")
            
    return render_template('voter_login.html')

@app.route('/voter/ballot', methods=['GET', 'POST'])
def voter_ballot():
    if 'voter_id' not in session: return redirect(url_for('voter_login'))
        
    if get_setting('status', 'Draft') != 'Active':
        session.clear()
        flash("Election is no longer active.", "danger")
        return redirect(url_for('voter_login'))
        
    voter = Voter.query.get(session['voter_id'])
    if not voter or voter.has_voted:
        session.clear()
        return redirect(url_for('voter_login'))
        
    candidates = Candidate.query.all()
    
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
            db.session.add(Vote(candidate_id=int(c_id)))
            
        voter.has_voted = True
        db.session.commit()
        
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
    
    candidates = Candidate.query.all()
    voters = Voter.query.all()
    status = get_setting('status', 'Draft')
    
    turnout = Vote.query.count()
    total = len(voters)
    pct = int((turnout / total) * 100) if total > 0 else 0
    
    # Calculate Results for Live Charting
    tally = []
    for c in candidates:
        votes_for_c = Vote.query.filter_by(candidate_id=c.id).count()
        tally.append({'name': c.name, 'count': votes_for_c})
    
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
    
    db.session.add(Candidate(
        name=request.form.get('name'), 
        party=request.form.get('party', 'Independent'), 
        bio=request.form.get('bio')
    ))
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/add_voter', methods=['POST'])
def api_add_voter():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    
    email = request.form.get('email').lower().strip()
    if Voter.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
    else:
        db.session.add(Voter(
            name=request.form.get('name'), 
            email=email, 
            pin=generate_pin()
        ))
        db.session.commit()
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
    Vote.query.delete()
    for v in Voter.query.all():
        v.has_voted = False
        v.pin = generate_pin()
    set_setting('status', 'Draft')
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/delete_candidate/<int:id>', methods=['POST'])
def api_delete_candidate(id):
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Candidate.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/delete_voter/<int:id>', methods=['POST'])
def api_delete_voter(id):
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Voter.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/clear_candidates', methods=['POST'])
def api_clear_candidates():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Vote.query.delete()
    Candidate.query.delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/api/clear_voters', methods=['POST'])
def api_clear_voters():
    if not session.get('admin_logged_in') or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Voter.query.delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
