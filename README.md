# BIET Government Election System 🏛️

An official, highly secure, and high-performance digital voting portal designed for the **Autonomous Constitutional Authority of BIET**. 

## Features
- **Public Information Dashboard**: A public-facing portal for citizens to view election updates, candidate manifestos, and final results.
- **Secure Voter Authentication**: Multi-factor identity verification using Registered Email and a 6-character cryptographic PIN.
- **Secret Ballot Box**: Complete separation of voter identity and vote records to guarantee absolute anonymity.
- **Control Room Dashboard**: A master admin interface to manage the electoral roll, add candidates, and control the election lifecycle (Draft -> Active -> Closed).
- **Live Result Charting**: Real-time visual bar charts rendering vote tallies instantly using Chart.js.

## Tech Stack
- **Backend Architecture**: Flask (Python)
- **Database Model**: Normalized relational SQL database via Flask-SQLAlchemy
- **Frontend Design**: Custom CSS (Glassmorphism, Official Government theme)
- **Data Visualization**: Chart.js

## Installation & Deployment

### Local Development
1. Clone the repository to your local machine.
2. Run the `run_voting.bat` script. This will automatically:
   - Create an isolated Python virtual environment.
   - Install all required dependencies from `requirements.txt`.
   - Boot the Flask server securely on port `8501`.

### Cloud / Live Deployment
This system is configured for seamless deployment to the cloud.
To switch from the local SQLite testing database to a live production database (e.g., PostgreSQL on AWS, Render, Heroku):
1. Simply inject a `DATABASE_URL` environment variable into your hosting provider's dashboard.
2. The application will instantly override the local database and write all election data to your cloud database automatically!

## Authorized Access Control
- **Public Portal**: `http://localhost:8501/`
- **Voter Authentication**: `http://localhost:8501/voter/login`
- **Control Room (Admin)**: `http://localhost:8501/admin/login`
  - *Default Officer Credentials: `admin` / `admin123`*

---
*Warning: Unauthorized access to the Control Room is strictly monitored and prohibited by law.*
