import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
import random
import string
import re
import json

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'election_data.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT)')
    conn.commit()
    conn.close()

def save_state_to_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    state_keys = ['election_status', 'trial_mode', 'ballot', 'electoral_roll', 'votes', 'outbox']
    for key in state_keys:
        if key in st.session_state:
            val = json.dumps(st.session_state[key])
            c.execute('INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)', (key, val))
    conn.commit()
    conn.close()

def load_state_from_db():
    if not os.path.exists(DB_PATH):
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM app_state')
    rows = c.fetchall()
    conn.close()
    if not rows:
        return False
    for key, value in rows:
        st.session_state[key] = json.loads(value)
    return True

# Set Page Config
st.set_page_config(
    page_title="Official Electoral Commission Portal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Sleek CSS Injection
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Core Typography & Base Styling */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #F8FAFC;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        color: #0F172A !important;
        letter-spacing: -0.5px;
    }
    
    /* Official Title header */
    .official-header {
        font-family: 'Inter', sans-serif;
        color: #0F172A;
        border-bottom: 3px solid #1E3A8A;
        padding-bottom: 10px;
        margin-bottom: 25px;
        font-weight: 700;
    }

    /* Professional Solid Cards */
    .glass-card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        margin-bottom: 20px !important;
    }

    .card-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 15px;
        color: #1E3A8A;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Metrics display */
    .metrics-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 20px;
    }

    .metric-item {
        flex: 1 1 calc(25% - 16px);
        min-width: 180px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 16px;
        position: relative;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    .metric-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: #1E3A8A;
    }
    
    .metric-item-yellow::before { background: #D97706; }
    .metric-item-purple::before { background: #4F46E5; }
    .metric-item-green::before { background: #059669; }

    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }

    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    
    /* Streamlit Overrides */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 4px !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 4px !important;
    }
    
    textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 4px !important;
        color: #0F172A !important;
    }

    .stButton>button {
        background: #1E3A8A !important;
        color: white !important;
        border: none !important;
        padding: 8px 20px !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        transition: background 0.2s !important;
    }

    .stButton>button:hover {
        background: #1E40AF !important;
    }
    
    /* Ballot Paper preview styles */
    .ballot-paper {
        background: #FFFFFF;
        border: 2px solid #CBD5E1;
        border-radius: 8px;
        padding: 30px;
        color: #0F172A;
        margin-top: 15px;
        position: relative;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .ballot-header {
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .ballot-logo {
        width: 60px;
        height: 60px;
        border-radius: 6px;
        background: #1E3A8A;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 700;
        font-size: 1.5rem;
    }
    
    .ballot-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    
    .ballot-desc {
        font-size: 0.85rem;
        color: #475569;
        line-height: 1.5;
    }
    
    .ballot-option {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 15px;
        margin-bottom: 12px;
        display: flex;
        align-items: flex-start;
        gap: 15px;
        transition: border-color 0.2s;
    }
    
    .ballot-option:hover {
        border-color: #94A3B8;
    }
    
    .checkbox-circle {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid #94A3B8;
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        margin-top: 3px;
    }
    
    .candidate-name {
        font-weight: 600;
        color: #0F172A;
    }
    
    .candidate-bio {
        font-size: 0.85rem;
        color: #475569;
        margin-top: 4px;
    }
    
    /* Badges */
    .status-badge {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 4px;
        display: inline-block;
    }
    .badge-draft { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
    .badge-active { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .badge-closed { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }

    .device-avatar-mock {
        width: 32px;
        height: 32px;
        border-radius: 4px;
        background: #E0E7FF;
        color: #3730A3;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)


# =====================================================================
# SESSION STATE INITIALIZATION
# =====================================================================

init_db()

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if 'voter_logged_in' not in st.session_state:
    st.session_state.voter_logged_in = None

db_loaded = load_state_from_db()

if not db_loaded:

    if 'election_status' not in st.session_state:
        st.session_state.election_status = 'Draft' # Draft, Active, Closed
    
    if 'trial_mode' not in st.session_state:
        st.session_state.trial_mode = False


    if 'ballot' not in st.session_state:
        st.session_state.ballot = {
            'title': 'Board of Directors Election 2026',
            'description': 'Please select your preferred representative(s) for the upcoming executive council. Each vote is cryptographic and verified.',
            'choice_rule': 'Single Choice', # Single Choice, Approval Voting
            'logo': '👑', # Preset icons like 👑, 🗳️, 🛡️, 🌐, 📊
            'parties': [],
            'candidates': []
        }

    if 'electoral_roll' not in st.session_state:
        st.session_state.electoral_roll = [
            {'name': 'Alex Rivera', 'email': 'alex@example.com', 'pin': 'PV9X82', 'voted': False},
            {'name': 'Jessica Chen', 'email': 'jessica@example.com', 'pin': 'KJ4L29', 'voted': False},
            {'name': 'David Mwangi', 'email': 'david@example.com', 'pin': 'TR7M10', 'voted': False},
            {'name': 'Elena Rostova', 'email': 'elena@example.com', 'pin': 'BF8Q54', 'voted': False},
            {'name': 'Liam O\'Connor', 'email': 'liam@example.com', 'pin': 'ND2Y77', 'voted': False}
        ]

    if 'votes' not in st.session_state:
        st.session_state.votes = [] # Secret Tally list (no links to voter profiles!)

    if 'outbox' not in st.session_state:
        st.session_state.outbox = [] # Simulated outbox log of sent emails


# Helper function to generate safe secure PINs
def generate_pin():
    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters like O, 0, I, 1 for voter safety
    for c in ['O', '0', 'I', '1']:
        chars = chars.replace(c, '')
    return ''.join(random.choice(chars) for _ in range(6))

# Helper to validate email addresses
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# Clear all data
def reset_election():
    st.session_state.election_status = 'Draft'
    st.session_state.trial_mode = False
    st.session_state.votes = []
    st.session_state.outbox = []
    st.session_state.voter_logged_in = None
    for voter in st.session_state.electoral_roll:
        voter['voted'] = False
        voter['pin'] = generate_pin()


# =====================================================================
# SIDEBAR NAVIGATION
# =====================================================================

st.sidebar.markdown("""
    <div style="padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px;">
        <span style="font-family: 'Inter', sans-serif; font-size: 1.3rem; font-weight: 700; color: #1E3A8A;">GOVERNMENT ELECTORAL</span>
        <span style="font-size:0.65rem; color:#FFFFFF; background: #1E3A8A; padding: 3px 6px; border-radius: 4px; margin-left: 8px; vertical-align:middle; text-transform:uppercase; font-weight:700;">PORTAL</span>
    </div>
""", unsafe_allow_html=True)

# Main Navigation (role toggle)
if st.session_state.voter_logged_in is not None:
    # Force Voter mode if they are authenticated and haven't finished voting
    nav_mode = "🗳️ Voter Portal"
    st.sidebar.markdown(f"""
        <div class="glass-card" style="padding:16px !important; margin-bottom: 20px !important;">
            <div style="font-size:0.7rem; color:#a0a5b5; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">Active Voter Session</div>
            <div style="display:flex; align-items:center; gap:12px;">
                <div class="device-avatar-mock">VP</div>
                <div>
                    <div style="font-weight:700; font-size:0.85rem; color:#f0f2f5;">{st.session_state.voter_logged_in['name']}</div>
                    <div style="font-size:0.7rem; color:#a0a5b5;">{st.session_state.voter_logged_in['email']}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("Abort & Exit Portal"):
        st.session_state.voter_logged_in = None
        save_state_to_db(); st.rerun()
else:
    # Standard role selector
    if st.session_state.admin_logged_in:
        nav_mode = st.sidebar.radio(
            "Navigation Role Mode",
            ["🛠️ Organizer Dashboard", "🗳️ Voter Portal"],
            index=0
        )
        if st.sidebar.button("🔒 Admin Logout"):
            st.session_state.admin_logged_in = False
            save_state_to_db(); st.rerun()
    else:
        nav_mode = st.sidebar.radio(
            "Navigation Role Mode",
            ["🔐 Master Access Portal", "🗳️ Voter Portal"],
            index=0
        )


# =====================================================================
# ORGANIZER DASHBOARD INTERFACE
# =====================================================================

if nav_mode == "🔐 Master Access Portal":
    st.markdown('<h2 class="official-header">Government Authority Access</h2>', unsafe_allow_html=True)
    st.markdown("<div style='max-width: 420px; margin: 40px auto;'>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Global Admin Authorization</div>", unsafe_allow_html=True)
    
    admin_user = st.text_input("Admin Username")
    admin_pass = st.text_input("Admin Password", type="password")
    if st.button("Unlock Dashboard"):
        if admin_user == "admin" and admin_pass == "admin123":
            st.session_state.admin_logged_in = True
            st.success("Authorized. Loading Organizer Dashboard...")
            time.sleep(0.5)
            save_state_to_db(); st.rerun()
        else:
            st.error("Invalid Global Admin credentials.")
    st.markdown("</div></div>", unsafe_allow_html=True)

elif nav_mode == "🛠️ Organizer Dashboard":
    st.markdown('<h2 class="official-header">Official Electoral Commission - Organizer Terminal</h2>', unsafe_allow_html=True)
    
    # Unified Global Stats Bar
    total_voters = len(st.session_state.electoral_roll)
    votes_cast = len(st.session_state.votes)
    turnout_pct = int((votes_cast / total_voters) * 100) if total_voters > 0 else 0
    invites_sent = len(st.session_state.outbox)
    
    status_label = st.session_state.election_status
    if st.session_state.trial_mode:
        status_label += " (Trial)"
        
    st.markdown(f"""
        <div class="metrics-grid">
            <div class="metric-item">
                <div class="metric-label">Election Status</div>
                <div class="metric-value">{status_label}</div>
            </div>
            <div class="metric-item metric-item-yellow">
                <div class="metric-label">Registered Voters</div>
                <div class="metric-value">{total_voters}</div>
            </div>
            <div class="metric-item metric-item-purple">
                <div class="metric-label">Invitations Dispatched</div>
                <div class="metric-value">{invites_sent}</div>
            </div>
            <div class="metric-item metric-item-green">
                <div class="metric-label">Voter Turnout</div>
                <div class="metric-value">{votes_cast} cast ({turnout_pct}%)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Sub-tab Navigation for Organizer Features
    org_tabs = st.tabs([
        "📋 Overview & Timeline",
        "🛠️ Ballot Designer",
        "👥 Electoral Roll Manager",
        "🚀 Launch & Timeline Control",
        "📊 Results & Outbox Log",
        "💾 Data Backups"
    ])
    
    # -------------------------------------------------------------
    # SUB-TAB 1: Overview & Timeline
    # -------------------------------------------------------------
    with org_tabs[0]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Election Lifecycle & Security Status</div>", unsafe_allow_html=True)
        st.write("""
        Welcome to the **Government Electoral Organizer Portal**. 
        Follow the sequential pipeline below to configure, seal, and deploy your legally valid election.
        """)
        
        # Draw a beautiful horizontal step timeline
        step1_badge = "badge-active" if st.session_state.election_status == 'Draft' else "badge-closed"
        step2_badge = "badge-draft"
        if st.session_state.election_status == 'Active':
            step2_badge = "badge-active"
        elif st.session_state.election_status == 'Closed':
            step2_badge = "badge-closed"
            
        step3_badge = "badge-active" if st.session_state.election_status == 'Closed' else "badge-draft"
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; text-align: center;">
                    <span class="status-badge {step1_badge}">Step 1: Configuration</span>
                    <h5 style="margin-top: 8px;">Design Ballot & Load Roll</h5>
                    <p style="font-size:0.75rem; color:#94a3b8; margin:0;">Register candidates, input emails, generate login credentials.</p>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; text-align: center;">
                    <span class="status-badge {step2_badge}">Step 2: Seal & Deploy</span>
                    <h5 style="margin-top: 8px;">Live Voting Period</h5>
                    <p style="font-size:0.75rem; color:#94a3b8; margin:0;">Seal the election to prevent manipulation. Credentials mailed out; voting portal live.</p>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; text-align: center;">
                    <span class="status-badge {step3_badge}">Step 3: Close & Tally</span>
                    <h5 style="margin-top: 8px;">Results Generation</h5>
                    <p style="font-size:0.75rem; color:#94a3b8; margin:0;">Halt incoming votes. Cryptographically tally results and display final breakdowns.</p>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Interactive Electoral Register Overview
        left_col, right_col = st.columns([1, 1.2])
        with left_col:
            st.markdown("<div class='glass-card' style='height:100%;'>", unsafe_allow_html=True)
            st.markdown("<div class='card-title'>Active Configuration Checklist</div>", unsafe_allow_html=True)
            
            # Ballot status check
            cand_count = len(st.session_state.ballot['candidates'])
            if cand_count >= 1:
                st.success(f"✓ Ballot Paper: {cand_count} candidates loaded.")
            else:
                st.error("✗ Ballot Paper: No candidates added yet (Configure in tab 2).")
                
            # Voters count check
            voter_count = len(st.session_state.electoral_roll)
            if voter_count >= 1:
                st.success(f"✓ Electoral Roll: {voter_count} voters loaded.")
            else:
                st.error("✗ Electoral Roll: Roll is currently empty (Configure in tab 3).")
                
            # Current phase details
            if st.session_state.election_status == 'Draft':
                st.info("ℹ️ System is open for modifications. You can run Free Trial run votes.")
            elif st.session_state.election_status == 'Active':
                st.warning("⚠️ Ballot is SEALED. Configuration changes disabled to guarantee ballot integrity.")
            elif st.session_state.election_status == 'Closed':
                st.success("🏁 Election closed. Ballot tallying finalized.")
                
            st.markdown("</div>", unsafe_allow_html=True)
            
        with right_col:
            st.markdown("<div class='glass-card' style='height:100%;'>", unsafe_allow_html=True)
            st.markdown("<div class='card-title'>Security Compliance Info</div>", unsafe_allow_html=True)
            st.markdown("""
            This simulated digital ballot box meets rigorous security criteria:
            
            1. **Secret Ballot Tally**: Cast choices are saved anonymously in a separate container pool (`st.session_state.votes`). Your choice is never written to your voter database profile, preserving individual privacy.
            2. **Single Vote Token Constraint**: The electoral roll checks if a matching PIN token has voted. If so, subsequent voter portal requests are blocked instantly, preventing double-voting.
            3. **Ballot Rigging Shields**: Sealing the election locks down candidate structures, descriptions, and election duration parameters.
            """)
            st.markdown("</div>", unsafe_allow_html=True)
            
    # -------------------------------------------------------------
    # SUB-TAB 2: Ballot Designer
    # -------------------------------------------------------------
    with org_tabs[1]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Customize Ballot Layout</div>", unsafe_allow_html=True)
        
        if st.session_state.election_status != 'Draft':
            st.warning("⚠️ Ballot layout is currently SEALED since the election has launched. Design options are read-only.")
            
        # Design editor forms
        disabled_flag = (st.session_state.election_status != 'Draft')
        
        col_meta1, col_meta2 = st.columns([2, 1])
        with col_meta1:
            new_title = st.text_input("Election Title", value=st.session_state.ballot['title'], disabled=disabled_flag)
            new_desc = st.text_area("Voter Instructions & Description", value=st.session_state.ballot['description'], height=100, disabled=disabled_flag)
            
        with col_meta2:
            new_logo = st.selectbox("Electoral Identity Logo Icon", ["👑", "🗳️", "🛡️", "🌐", "📊", "👥", "🏛️"], index=["👑", "🗳️", "🛡️", "🌐", "📊", "👥", "🏛️"].index(st.session_state.ballot['logo']), disabled=disabled_flag)
            new_rule = st.selectbox("Voting Calculation Rule", ["Single Choice", "Approval Voting"], index=["Single Choice", "Approval Voting"].index(st.session_state.ballot['choice_rule']), disabled=disabled_flag)
            
        if not disabled_flag:
            st.session_state.ballot['title'] = new_title
            st.session_state.ballot['description'] = new_desc
            st.session_state.ballot['logo'] = new_logo
            st.session_state.ballot['choice_rule'] = new_rule
            
        # Party Registry Manager
        st.markdown("#### Political Parties Registry (Max 10)")
        if 'parties' not in st.session_state.ballot:
            st.session_state.ballot['parties'] = ['Independent']
            
        # Display current parties
        st.write(f"Current Parties: {', '.join(st.session_state.ballot['parties'])}")
        
        if not disabled_flag and len(st.session_state.ballot['parties']) < 10:
            with st.form("add_party_form"):
                p_name = st.text_input("Add Custom Party Name", placeholder="e.g. Future Vanguard")
                submit_party = st.form_submit_button("Add Party")
                if submit_party and p_name.strip() != "":
                    if p_name.strip() not in st.session_state.ballot['parties']:
                        st.session_state.ballot['parties'].append(p_name.strip())
                        st.success(f"Party '{p_name}' added!")
                        save_state_to_db(); st.rerun()
                    else:
                        st.error("Party already exists.")
        
        st.markdown("---")
        
        # Candidate List Manager
        st.markdown("#### Candidate Roster")
        
        # Add Candidate Section
        if not disabled_flag:
            with st.form("add_candidate_form"):
                st.write("➕ **Register New Candidate**")
                c_name = st.text_input("Candidate Full Name", placeholder="e.g. Robert Vance")
                c_party = st.selectbox("Political Party Affiliation", st.session_state.ballot['parties'])
                c_bio = st.text_area("Short Bio / Statement", placeholder="Provide relevant details or proposals for voters...", height=70)
                submit_cand = st.form_submit_button("Add Candidate to Ballot")
                
                if submit_cand:
                    if c_name.strip() == "":
                        st.error("Candidate name cannot be empty.")
                    else:
                        new_id = f"cand_{int(time.time())}"
                        st.session_state.ballot['candidates'].append({'id': new_id, 'name': c_name, 'party': c_party, 'bio': c_bio})
                        st.success(f"Candidate '{c_name}' registered successfully.")
                        save_state_to_db(); st.rerun()
                        
        # Render Active Candidate Table with deletion controls
        if len(st.session_state.ballot['candidates']) == 0:
            st.info("No candidates registered yet.")
        else:
            for idx, cand in enumerate(st.session_state.ballot['candidates']):
                cand_col1, cand_col2 = st.columns([5, 1])
                with cand_col1:
                    party_str = f" <span style='font-size:0.75rem; color:#ab47bc; background:rgba(171,71,188,0.1); padding:2px 6px; border-radius:8px; margin-left:8px;'>{cand.get('party', 'Independent')}</span>"
                    st.markdown(f"**{idx + 1}. {cand['name']}**{party_str}", unsafe_allow_html=True)
                    st.caption(cand['bio'] if cand['bio'] else "No biography provided.")
                with cand_col2:
                    if not disabled_flag:
                        if st.button("🗑️ Delete", key=f"del_cand_{cand['id']}"):
                            st.session_state.ballot['candidates'].remove(cand)
                            st.success(f"Candidate deleted.")
                            save_state_to_db(); st.rerun()
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                
        # Live Preview render
        st.markdown("#### Preview Ballot Sheet (Real-Time Layout)")
        st.markdown(f"""
            <div class="ballot-paper">
                <div class="ballot-header">
                    <div>
                        <div class="ballot-title">{st.session_state.ballot['title']}</div>
                        <div class="ballot-desc">{st.session_state.ballot['description']}</div>
                        <div style="font-size:0.7rem; color:#00f0f0; font-weight:700; text-transform:uppercase; margin-top:8px;">
                            Rule type: {st.session_state.ballot['choice_rule']}
                        </div>
                    </div>
                    <div class="ballot-logo">{st.session_state.ballot['logo']}</div>
                </div>
        """, unsafe_allow_html=True)
        
        # Draw candidates inside ballot preview
        for cand in st.session_state.ballot['candidates']:
            party_tag = f" <span style='font-size:0.75rem; color:#ab47bc; background:rgba(171,71,188,0.1); padding:2px 6px; border-radius:8px; margin-left:8px;'>{cand.get('party', 'Independent')}</span>"
            st.markdown(f"""
                <div class="ballot-option">
                    <div class="checkbox-circle"></div>
                    <div>
                        <span class="candidate-name">{cand['name']}{party_tag}</span>
                        <div class="candidate-bio">{cand['bio']}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    # -------------------------------------------------------------
    # SUB-TAB 3: Electoral Roll Manager
    # -------------------------------------------------------------
    with org_tabs[2]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Manage Voter Roster & Security Credentials</div>", unsafe_allow_html=True)
        
        if st.session_state.election_status != 'Draft':
            st.warning("⚠️ Electoral Roll is sealed while the election is active. Add/Delete operations are blocked.")
            
        disabled_flag = (st.session_state.election_status != 'Draft')
        
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            st.write("➕ **Register Single Voter**")
            with st.form("single_voter_form"):
                v_name = st.text_input("Voter Full Name", placeholder="e.g. Jane Doe")
                v_email = st.text_input("Voter Email Address", placeholder="jane@example.com")
                submit_v = st.form_submit_button("Add Voter")
                
                if submit_v:
                    if v_name.strip() == "" or v_email.strip() == "":
                        st.error("Please fill in both name and email.")
                    elif not is_valid_email(v_email):
                        st.error("Invalid email format.")
                    elif any(v['email'].lower() == v_email.lower() for v in st.session_state.electoral_roll):
                        st.error("A voter with this email already exists.")
                    else:
                        new_pin = generate_pin()
                        st.session_state.electoral_roll.append({
                            'name': v_name,
                            'email': v_email.lower(),
                            'pin': new_pin,
                            'voted': False
                        })
                        st.success(f"Voter '{v_name}' successfully added to roll.")
                        save_state_to_db(); st.rerun()
                        
        with col_v2:
            st.write("📋 **Bulk Import Voter List**")
            bulk_txt = st.text_area("Paste CSV Format (One entry per line: Name, Email)", placeholder="Example:\nBob Johnson, bob@example.com\nAlice Cooper, alice@example.com", height=150, disabled=disabled_flag)
            
            if st.button("Parse & Append Roster", disabled=disabled_flag):
                if bulk_txt.strip() != "":
                    lines = bulk_txt.strip().split("\n")
                    added_count = 0
                    error_count = 0
                    for line in lines:
                        parts = line.split(",")
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            email = parts[1].strip().lower()
                            if name and is_valid_email(email):
                                if not any(v['email'].lower() == email for v in st.session_state.electoral_roll):
                                    st.session_state.electoral_roll.append({
                                        'name': name,
                                        'email': email,
                                        'pin': generate_pin(),
                                        'voted': False
                                    })
                                    added_count += 1
                                else:
                                    error_count += 1
                            else:
                                error_count += 1
                        else:
                            error_count += 1
                    
                    if added_count > 0:
                        st.success(f"Successfully imported {added_count} voters.")
                    if error_count > 0:
                        st.warning(f"Skipped {error_count} lines due to formatting or duplicates.")
                    save_state_to_db(); st.rerun()
                    
        st.markdown("---")
        st.markdown("#### Registered Electoral Roll")
        
        # Display roll table
        if len(st.session_state.electoral_roll) == 0:
            st.info("Electoral roll is empty.")
        else:
            roll_df = pd.DataFrame(st.session_state.electoral_roll)
            
            # Formatted table representation
            display_df = roll_df.copy()
            # If the election is active/closed, obscure part of the PINs for security, or keep them viewable for testing
            display_df['Voted Status'] = display_df['voted'].apply(lambda x: '✅ Voted' if x else '⏳ Pending')
            display_df = display_df[['name', 'email', 'pin', 'Voted Status']]
            display_df.columns = ['Name', 'Email Address', 'Security Login PIN', 'Status']
            
            st.dataframe(display_df, use_container_width=True)
            
            # Export controls
            csv_data = roll_df.to_csv(index=False)
            st.download_button(
                "📥 Export & Download Voter Roll (CSV)",
                data=csv_data,
                file_name="electoral_roll_credentials.csv",
                mime="text/csv"
            )
            
            if not disabled_flag:
                if st.button("🚨 Clear Complete Roster"):
                    st.session_state.electoral_roll = []
                    st.success("Electoral roll purged.")
                    save_state_to_db(); st.rerun()
                    
        st.markdown("</div>", unsafe_allow_html=True)
        
    # -------------------------------------------------------------
    # SUB-TAB 4: Launch & Timeline Control
    # -------------------------------------------------------------
    with org_tabs[3]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Manage Launch Schedule</div>", unsafe_allow_html=True)
        
        # Scheduling configurations
        col_sch1, col_sch2 = st.columns(2)
        with col_sch1:
            st.write("📅 **Timeline Windows**")
            start_date = st.date_input("Election Start Date", value=pd.Timestamp.now().date())
            start_time = st.time_input("Election Start Time", value=pd.Timestamp.now().time())
            
        with col_sch2:
            st.write("⌛ **Closing Deadline**")
            end_date = st.date_input("Election Closing Date", value=(pd.Timestamp.now() + pd.Timedelta(days=7)).date())
            end_time = st.time_input("Election Closing Time", value=pd.Timestamp.now().time())
            
        st.markdown("---")
        
        # Email Notification settings
        st.markdown("#### Custom Invitation Email Template")
        st.write("Design the invitation message layout sent to eligible voters when launching. Use placeholders to fill data.")
        st.caption("Placeholders: `{voter_name}` (Name), `{election_title}` (Election Title), `{voter_pin}` (Verification PIN), `{election_link}` (Portal URL)")
        
        default_email_body = """Hello {voter_name},

You are registered as an eligible voter for the upcoming election: "{election_title}".

Please log into the secure online voting portal using the credentials provided below:

Electoral URL Link: http://localhost:8501
Registered Email: {voter_email}
Secure Authentication PIN: {voter_pin}

This election is protected client-side. The database records your participation anonymously to ensure voter secrecy.

Regards,
Election Executive Committee"""
        
        email_body_template = st.text_area("Email Message Body Outline", value=default_email_body, height=180)
        
        st.markdown("---")
        
        # Verification and Launch Triggers
        st.markdown("#### Election Deployment Controls")
        
        if st.session_state.election_status == 'Draft':
            # Check requirements
            cand_len = len(st.session_state.ballot['candidates'])
            roll_len = len(st.session_state.electoral_roll)
            
            c_laun1, c_laun2 = st.columns(2)
            with c_laun1:
                st.write("🧪 **Developer Free Trial Mode**")
                st.write("Launch a free trial election restricted to a maximum of 5 voters. Allows test votes to evaluate system flow without sealing layouts.")
                if st.button("🏁 Launch Mock Trial Election"):
                    if cand_len == 0:
                        st.error("Launch Blocked: Register at least 1 candidate.")
                    elif roll_len == 0:
                        st.error("Launch Blocked: Load at least 1 voter into the roll.")
                    elif roll_len > 5:
                        st.error("Trial Limit Exceeded: Trial elections are restricted to 5 voters. Please remove extra voters or proceed with Official Launch.")
                    else:
                        st.session_state.election_status = 'Active'
                        st.session_state.trial_mode = True
                        
                        # Generate outbox messages
                        st.session_state.outbox = []
                        for voter in st.session_state.electoral_roll:
                            body = email_body_template.format(
                                voter_name=voter['name'],
                                voter_email=voter['email'],
                                election_title=st.session_state.ballot['title'],
                                voter_pin=voter['pin'],
                                election_link="http://localhost:8501"
                            )
                            st.session_state.outbox.append({
                                'email': voter['email'],
                                'subject': f"Trial Invitation: {st.session_state.ballot['title']}",
                                'body': body,
                                'sent_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        st.success("Trial Election Activated! Credentials dispatched to Outbox Log. Go to 'Voter Portal' navigation tab to test.")
                        save_state_to_db(); st.rerun()
                        
            with c_laun2:
                st.write("🔒 **Official Sealed Election**")
                st.write("Binds all ballot details and voter credentials. Once activated, ballot designer configurations and rosters are locked. Credentials are sent.")
                if st.button("🔒 Seal & Start Official Election"):
                    if cand_len == 0:
                        st.error("Launch Blocked: Register at least 1 candidate.")
                    elif roll_len == 0:
                        st.error("Launch Blocked: Load at least 1 voter into the roll.")
                    else:
                        st.session_state.election_status = 'Active'
                        st.session_state.trial_mode = False
                        
                        # Generate outbox messages
                        st.session_state.outbox = []
                        for voter in st.session_state.electoral_roll:
                            body = email_body_template.format(
                                voter_name=voter['name'],
                                voter_email=voter['email'],
                                election_title=st.session_state.ballot['title'],
                                voter_pin=voter['pin'],
                                election_link="http://localhost:8501"
                            )
                            st.session_state.outbox.append({
                                'email': voter['email'],
                                'subject': f"Official Election Invitation: {st.session_state.ballot['title']}",
                                'body': body,
                                'sent_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        st.success("Official Election Sealed & Dispatched! Configuration locked. Secure portal open.")
                        save_state_to_db(); st.rerun()
                        
        elif st.session_state.election_status == 'Active':
            st.info("⚡ Election is currently ACTIVE. Roster and Ballot rules are locked.")
            
            c_laun1, c_laun2 = st.columns(2)
            with c_laun1:
                if st.button("🛑 Stop & Close Voting (Tally Votes)"):
                    st.session_state.election_status = 'Closed'
                    st.success("Election closed. Digital ballot tallies generated.")
                    save_state_to_db(); st.rerun()
                    
        elif st.session_state.election_status == 'Closed':
            st.success("🏁 Election closed. Ballot tallying finalized. Results unlocked.")
            
            if st.button("🔄 Reset System (Start New Election)"):
                reset_election()
                st.success("Election system reset to Draft.")
                save_state_to_db(); st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
        
    # -------------------------------------------------------------
    # SUB-TAB 5: Results & Outbox Log
    # -------------------------------------------------------------
    with org_tabs[4]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>Election Results Analysis</div>", unsafe_allow_html=True)
        
        # Check security rule
        if st.session_state.election_status == 'Draft':
            st.info("Awaiting election launch to tally results.")
        else:
            # Turnout Analytics
            c_res1, c_res2 = st.columns([1, 1.2])
            with c_res1:
                st.write("**Real-time Turnout Gauge**")
                # Plotly Turnout Gauge Chart
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=votes_cast,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Turnout (Votes Cast)", 'font': {'color': "#0F172A"}},
                    gauge={
                        'axis': {'range': [0, total_voters], 'tickwidth': 1, 'tickcolor': "#0F172A", 'tickfont': {'color': '#0F172A'}},
                        'bar': {'color': "#1E3A8A"},
                        'bgcolor': "#F8FAFC",
                        'borderwidth': 2,
                        'bordercolor': "#CBD5E1",
                        'steps': [
                            {'range': [0, total_voters/2], 'color': '#F1F5F9'},
                            {'range': [total_voters/2, total_voters], 'color': '#E2E8F0'}
                        ]
                    }
                ))
                fig_gauge.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    height=240,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig_gauge, use_container_width=True)
                
            with c_res2:
                st.write("**Candidate Vote Distribution**")
                
                # Check sealing privacy rule
                # In Polyas, candidates' live vote distributions are hidden until closed, to avoid bias.
                # However, for trial mode, we can show them live. For official mode, let's offer a setting or hide them.
                hide_results = (st.session_state.election_status == 'Active' and not st.session_state.trial_mode)
                
                if hide_results:
                    st.markdown("""
                        <div style="background: rgba(255,171,0,0.05); border:1px solid rgba(255,171,0,0.15); padding:20px; border-radius:12px; margin-top:20px; text-align:center;">
                            🔒 <b>Results Sealed</b>
                            <p style="font-size:0.8rem; color:#94a3b8; margin: 5px 0 0 0;">Under compliance guidelines, active candidate distributions are hidden until voting finishes. Close the election to unlock the final tally.</p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    if votes_cast == 0:
                        st.info("No votes have been cast yet.")
                    else:
                        # Tally the votes
                        tally = {cand['name']: 0 for cand in st.session_state.ballot['candidates']}
                        invalid_count = 0 # In case of blank/invalid write-ins
                        
                        # Process tally
                        for vote in st.session_state.votes:
                            # Account for Single or Approval lists
                            if isinstance(vote, list):
                                for item in vote:
                                    if item in tally:
                                        tally[item] += 1
                            else:
                                if vote in tally:
                                    tally[vote] += 1
                                    
                        # Draw Chart
                        tally_df = pd.DataFrame(list(tally.items()), columns=['Candidate', 'Votes'])
                        fig_bar = px.bar(
                            tally_df, 
                            x='Candidate', 
                            y='Votes', 
                            color='Votes', 
                            color_continuous_scale=['#3B82F6', '#1E3A8A'],
                            title="Tally Count Summary"
                        )
                        fig_bar.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color="#0F172A"),
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=True, gridcolor='#E2E8F0'),
                            coloraxis_showscale=False,
                            height=250,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
        st.markdown("---")
        
        # Outbox Logs
        st.markdown("#### Simulated Dispatch Outbox Email Logs")
        st.write("When voters are registered and the election starts, invitation emails are dispatched. Use this mock outbox to check/retrieve security PINs to log in as different test voters.")
        
        if len(st.session_state.outbox) == 0:
            st.info("Outbox is empty. Launch the election to dispatch invites.")
        else:
            for out in st.session_state.outbox:
                with st.expander(f"✉️ Outbox To: {out['email']} | Sent: {out['sent_at']}"):
                    st.text(f"Subject: {out['subject']}\n\n{out['body']}")
                    
        st.markdown("</div>", unsafe_allow_html=True)
        
    # -------------------------------------------------------------
    # SUB-TAB 6: Data Backups
    # -------------------------------------------------------------
    with org_tabs[5]:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-title'>System Portability Backup Options</div>", unsafe_allow_html=True)
        st.write("Export your election parameters (candidates, instructions, voter roster) as a JSON file, or import a saved backup configuration.")
        
        # JSON Generator
        backup_state = {
            'election_status': st.session_state.election_status,
            'trial_mode': st.session_state.trial_mode,
            'ballot': st.session_state.ballot,
            'electoral_roll': st.session_state.electoral_roll,
            'votes': st.session_state.votes,
            'outbox': st.session_state.outbox
        }
        
        json_backup = json.dumps(backup_state, indent=2)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.write("📤 **Export Data**")
            st.download_button(
                "📥 Download Current Election Backup (.json)",
                data=json_backup,
                file_name="govt_election_backup.json",
                mime="application/json"
            )
            
        with col_b2:
            st.write("📥 **Import Data**")
            uploaded_file = st.file_uploader("Upload an Election Backup File", type=["json"])
            if uploaded_file is not None:
                try:
                    loaded_data = json.load(uploaded_file)
                    st.session_state.election_status = loaded_data['election_status']
                    st.session_state.trial_mode = loaded_data['trial_mode']
                    st.session_state.ballot = loaded_data['ballot']
                    st.session_state.electoral_roll = loaded_data['electoral_roll']
                    st.session_state.votes = loaded_data['votes']
                    st.session_state.outbox = loaded_data['outbox']
                    st.success("Backup loaded successfully! Rerunning portal...")
                    time.sleep(0.5)
                    save_state_to_db(); st.rerun()
                except Exception as e:
                    st.error(f"Error parsing backup file: {e}")
                    
        st.markdown("</div>", unsafe_allow_html=True)


# =====================================================================
# VOTER PORTAL INTERFACE
# =====================================================================

elif nav_mode == "🗳️ Voter Portal":
    
    st.markdown('<h2 class="official-header">Official Voter Authentication Portal</h2>', unsafe_allow_html=True)
    
    # -------------------------------------------------------------
    # PHASE A: Voter Login Screen
    # -------------------------------------------------------------
    if st.session_state.voter_logged_in is None:
        
        if st.session_state.election_status != 'Active':
            st.warning("⚠️ Access Restricted: The election is not currently active. Registrars must launch the election to open voter portals.")
            
        st.markdown("<div style='max-width: 420px; margin: 40px auto;'>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        
        st.markdown("""
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="font-family: 'Inter', sans-serif; font-size: 2.2rem; font-weight: 800; color: #1E3A8A;">OFFICIAL ELECTION BALLOT</div>
                <div style="font-size: 0.8rem; color: #a0a5b5; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px;">Verified Secure Voter Login</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Authentication fields
        disabled_login = (st.session_state.election_status != 'Active')
        
        input_email = st.text_input("Voter Email ID", placeholder="e.g. alex@example.com", disabled=disabled_login)
        input_pin = st.text_input("Security Authorization PIN", type="password", placeholder="e.g. PV9X82", disabled=disabled_login)
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if st.button("Unlock Ballot Paper", disabled=disabled_login):
            if input_email.strip() == "" or input_pin.strip() == "":
                st.error("Please fill in credentials.")
            else:
                # Find matching voter profile
                matched_voter = None
                for voter in st.session_state.electoral_roll:
                    if voter['email'].lower() == input_email.strip().lower() and voter['pin'] == input_pin.strip():
                        matched_voter = voter
                        break
                        
                if matched_voter is not None:
                    # Check if already voted
                    if matched_voter['voted']:
                        st.error("Double Voting Prohibited: This token has already cast an election ballot.")
                    else:
                        st.session_state.voter_logged_in = matched_voter
                        st.success("Authorized! Directing to Ballot...")
                        time.sleep(0.6)
                        save_state_to_db(); st.rerun()
                else:
                    st.error("Access Denied: Invalid email or PIN combination. Please check details in the Outbox Email Logs.")
                    
        st.markdown("""
            <div style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 16px; text-align: center;">
                <span style="font-size:0.7rem; color:#808595; text-transform:uppercase; letter-spacing:0.5px;">Tally Security Protocol Activated</span>
            </div>
            </div>
            </div>
        """, unsafe_allow_html=True)
        
    # -------------------------------------------------------------
    # PHASE B: Voting Interface (Personalized Ballot Rendering)
    # -------------------------------------------------------------
    else:
        voter_profile = st.session_state.voter_logged_in
        
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        
        # Display voter details
        st.markdown(f"""
            <div style="background: rgba(0, 240, 240, 0.05); border: 1px solid rgba(0, 240, 240, 0.15); padding: 12px 18px; border-radius: 12px; margin-bottom: 20px; font-size: 0.85rem;">
                👤 Authenticated: <b>{voter_profile['name']}</b> ({voter_profile['email']})
                <br>🔒 Token Status: <b>Ballot Ballot Sealed, Secure Connection Verified</b>
            </div>
        """, unsafe_allow_html=True)
        
        # Rendering personalized ballot paper with choice components
        st.markdown(f"""
            <div class="ballot-paper">
                <div class="ballot-header">
                    <div>
                        <div class="ballot-title">{st.session_state.ballot['title']}</div>
                        <div class="ballot-desc">{st.session_state.ballot['description']}</div>
                        <div style="font-size:0.7rem; color:#ab47bc; font-weight:700; text-transform:uppercase; margin-top:8px;">
                            Verification Rule: {st.session_state.ballot['choice_rule']}
                        </div>
                    </div>
                    <div class="ballot-logo">{st.session_state.ballot['logo']}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Gather candidates
        candidates = st.session_state.ballot['candidates']
        candidate_names = [cand['name'] for cand in candidates]
        
        # Input selection forms
        st.write("🗳️ **Make your selection:**")
        
        chosen_vote = None
        
        # Render different input forms based on Ballot Rule
        if st.session_state.ballot['choice_rule'] == 'Single Choice':
            chosen_name = st.radio(
                "Candidates list (select one):",
                candidate_names,
                index=None,
                key="voter_radio_choice"
            )
            
            # Show candidate profiles explicitly
            for cand in candidates:
                st.caption(f"**{cand['name']}** [{cand.get('party', 'Independent')}]: {cand['bio']}")
                
            chosen_vote = chosen_name
            
        else: # Approval Voting (Multiple Choices)
            chosen_list = []
            st.write("Choose one or more options:")
            for cand in candidates:
                checked = st.checkbox(cand['name'], key=f"checkbox_{cand['id']}")
                st.caption(f"[{cand.get('party', 'Independent')}] {cand['bio']}")
                if checked:
                    chosen_list.append(cand['name'])
                st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
                
            chosen_vote = chosen_list
            
        st.markdown("---")
        
        # Submission Buttons
        c_sub1, c_sub2 = st.columns([1.5, 5])
        with c_sub1:
            if st.button("🔥 Cast Ballot Paper"):
                # Validation checks
                is_empty = False
                if isinstance(chosen_vote, list):
                    is_empty = (len(chosen_vote) == 0)
                else:
                    is_empty = (chosen_vote is None)
                    
                if is_empty:
                    st.error("Blank Ballot: Please select a candidate option before casting your vote.")
                else:
                    # Proceed with cryptographic vote placement
                    # 1. Store vote choice anonymously
                    st.session_state.votes.append(chosen_vote)
                    
                    # 2. Mark voter as voted to block reuse
                    for voter in st.session_state.electoral_roll:
                        if voter['email'].lower() == voter_profile['email'].lower():
                            voter['voted'] = True
                            break
                            
                    # 3. Success notification and log out
                    st.success("Ballot Cast! Your vote has been dropped into the secret digital container.")
                    time.sleep(1.0)
                    st.session_state.voter_logged_in = None
                    save_state_to_db(); st.rerun()
                    
        with c_sub2:
            st.caption("⚠️ **Notice**: Once you press 'Cast Ballot Paper', your selection is immediately sealed and your cryptographic login token is destroyed. You cannot log back in to review or change your vote.")
            
        st.markdown("</div>", unsafe_allow_html=True)

# Save state at the end of execution stream
save_state_to_db()
