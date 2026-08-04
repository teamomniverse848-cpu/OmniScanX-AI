# OmniScanX-AI (Cloud-Based Attendance Management System)

A robust, modern web application for tracking student attendance. Built with Python, Flask, and PostgreSQL (Supabase), featuring a stunning Glassmorphism UI, Google OAuth integration, and Two-Factor Authentication via Email OTP.

## Features

- **Role-Based Access Control**: Separate dashboards for Students and Teachers/Admins.
- **Modern UI/UX**: Premium Glassmorphism design with dynamic video backgrounds and Bootstrap 5.
- **Advanced Authentication**:
  - Secure local Signup/Login (Werkzeug Password Hashing)
  - Google OAuth 2.0 Integration
  - Email OTP Verification (2FA) for sensitive actions
- **Attendance Tracking**: 
  - Admins can mark students Present/Absent/Late.
  - Students can view their personal attendance history.
- **Export Data**: One-click CSV export of attendance records.
- **Cloud Database**: Powered by Supabase (PostgreSQL) for scalable, secure data storage.

## Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5, FontAwesome
- **Backend**: Python 3.13, Flask, Jinja2
- **Database**: PostgreSQL (Supabase) via `psycopg3`
- **Authentication**: Authlib, Flask-Mail, Werkzeug Security

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/teamomniverse848-cpu/OmniScanX-AI.git
   cd OmniScanX-AI
   ```

2. **Install Dependencies**
   Ensure you have Python 3.13+ installed.
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file in the root directory and add the following keys:
   ```env
   SECRET_KEY=your-random-secret-key
   SUPABASE_DB_URL=postgresql://postgres.[your-project]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret

   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-digit-app-password
   ```

4. **Initialize the Database**
   Copy the contents of `database/schema.sql` and run them in your Supabase SQL Editor to create the necessary tables and seed default departments.

5. **Run the Application**
   ```bash
   python app.py
   ```
   The app will be available at `http://127.0.0.1:5000`.

## Testing

Run the automated test suite using Python's built-in `unittest` framework:
```bash
python -m unittest tests/test_app.py
```

## License
MIT License. See `LICENSE` for more information.
