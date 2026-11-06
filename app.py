from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
from functools import wraps
import re
import os
import time
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_fallback')

admin_password_check = os.environ.get('ADMIN_PASSWORD', 'admin123')
if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$', admin_password_check):
    print("CRITICAL SECURITY WARNING: ADMIN_PASSWORD must be at least 8 characters, and contain a letter, a number, and a special character.")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token is missing or invalid'}), 401
        try:
            data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
            if not data.get('admin'):
                raise Exception()
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(*args, **kwargs)
    return decorated


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
    while True:
        pin = ''.join(random.choice(chars) for _ in range(6))
        if not Voter.query.filter_by(pin=pin).first():
            return pin

def send_pin_email(voter_email, voter_name, pin):
    mail_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    
    msg = MIMEMultipart()
    msg['From'] = f"Election Commission <{mail_username or 'noreply@election.gov'}>"
    msg['To'] = voter_email
    msg['Subject'] = "CONFIDENTIAL: Your Official Voter Authorization PIN"
    
    body = f"""
    Dear {voter_name},
    
    You have been successfully registered on the Official Electoral Roll.
    
    Your Secure Authorization PIN is: {pin}
    
    Please keep this PIN strictly confidential. You will need it, along with your registered email, to access the Secure Voting Portal.
    
    Regards,
    Election Commission
    """
    msg.attach(MIMEText(body, 'plain'))
    
    if not mail_username or not mail_password:
        print(f"WARNING: Email credentials missing. Saving email locally for {voter_email}")
        if not os.path.exists('temp_emails'):
            os.makedirs('temp_emails')
        filename = f"temp_emails/email_to_{voter_email.replace('@', '_at_')}.txt"
        with open(filename, 'w') as f:
            f.write(msg.as_string())
        return False
    
    try:
        server = smtplib.SMTP(mail_server, mail_port)
        server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

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
@limiter.limit('5 per minute')
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
        
    voter = db.session.get(Voter, session['voter_id'])
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
            
        # Validate candidate IDs and cast vote secretly
        valid_ids = {str(c.id) for c in candidates}
        for c_id in selections:
            if str(c_id) not in valid_ids:
                flash("Invalid candidate selected.", "danger")
                return redirect(url_for('voter_ballot'))
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
@limiter.limit('5 per minute')
def admin_login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@123!')
            
            if username == admin_username and password == admin_password:
                token = jwt.encode({'admin': True, 'exp': time.time() + 3600}, app.secret_key, algorithm="HS256")
                return jsonify({'token': token}), 200
            return jsonify({'message': 'Invalid Global Admin credentials.'}), 401
        return jsonify({'message': 'JSON format required'}), 400
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard_skeleton.html')

@app.route('/admin/api/dashboard_content', methods=['GET'])
@token_required
def api_dashboard_content():
    candidates = Candidate.query.all()
    voters = Voter.query.all()
    status = get_setting('status', 'Draft')
    
    turnout = Vote.query.count()
    total = len(voters)
    pct = int((turnout / total) * 100) if total > 0 else 0
    
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
@token_required
def api_add_candidate():
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    
    name = request.form.get('name', '').strip()
    if not name:
        flash("Candidate name cannot be empty.", "danger")
        return jsonify({'status': 'ok'}), 200
        
    db.session.add(Candidate(
        name=name, 
        party=request.form.get('party', 'Independent').strip() or 'Independent', 
        bio=request.form.get('bio', '').strip()
    ))
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/add_voter', methods=['POST'])
@token_required
def api_add_voter():
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    
    email = request.form.get('email', '').lower().strip()
    name = request.form.get('name', '').strip()
    
    if not email or not name:
        flash("Voter name and email cannot be empty.", "danger")
    elif Voter.query.filter_by(email=email).first():
        flash("Email already registered.", "danger")
    else:
        new_pin = generate_pin()
        db.session.add(Voter(
            name=name, 
            email=email, 
            pin=new_pin
        ))
        db.session.commit()
        
        # Send email
        if send_pin_email(email, name, new_pin):
            flash(f"Voter registered and email sent securely.", "success")
        else:
            flash(f"Voter registered, but email failed (Check SMTP settings). PIN: {new_pin}", "warning")
            
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/launch', methods=['POST'])
@token_required
def api_launch():
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    set_setting('status', 'Active')
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/close', methods=['POST'])
@token_required
def api_close():
    if False: return "Unauthorized", 401
    set_setting('status', 'Closed')
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/reset', methods=['POST'])
@token_required
def api_reset():
    if False: return "Unauthorized", 401
    Vote.query.delete()
    for v in Voter.query.all():
        v.has_voted = False
        v.pin = generate_pin()
    set_setting('status', 'Draft')
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/delete_candidate/<int:id>', methods=['POST'])
@token_required
def api_delete_candidate(id):
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Vote.query.filter_by(candidate_id=id).delete()
    Candidate.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/delete_voter/<int:id>', methods=['POST'])
@token_required
def api_delete_voter(id):
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Voter.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/clear_candidates', methods=['POST'])
@token_required
def api_clear_candidates():
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Vote.query.delete()
    Candidate.query.delete()
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/api/clear_voters', methods=['POST'])
@token_required
def api_clear_voters():
    if False or get_setting('status', 'Draft') != 'Draft': return "Unauthorized/Sealed", 401
    Voter.query.delete()
    db.session.commit()
    return jsonify({'status': 'ok'}), 200

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8501, debug=True)
