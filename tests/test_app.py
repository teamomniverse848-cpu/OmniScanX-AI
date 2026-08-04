import unittest
from app import app

class AttendanceSystemTestCase(unittest.TestCase):

    def setUp(self):
        """Set up a blank temp database before each test and initialize test client."""
        # Config app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        # We use Flask's test_client to simulate HTTP requests without running a live server
        self.client = app.test_client()

    def tearDown(self):
        """Clean up after each test."""
        pass

    def test_homepage_redirects(self):
        """Test that the root route redirects to the login page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302) # 302 is the HTTP code for Redirect
        self.assertIn(b'/login', response.data)

    def test_login_page_loads(self):
        """Test that the login page renders successfully with our Glassmorphism UI."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.data) # Check for HTML text
        self.assertIn(b'glass-card', response.data) # Check for UI class

    def test_unauthorized_dashboard_access(self):
        """Test that accessing dashboards without session redirects to login."""
        # Try Admin Dashboard
        admin_resp = self.client.get('/admin_dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized access!', admin_resp.data)
        
        # Try Student Dashboard
        student_resp = self.client.get('/student_dashboard', follow_redirects=True)
        self.assertIn(b'Unauthorized access!', student_resp.data)

    def test_invalid_login_credentials(self):
        """Test that a wrong password returns an error flash message."""
        response = self.client.post('/login', data=dict(
            username='admin',
            password='wrong_password123'
        ), follow_redirects=True)
        
        # Ensure it didn't log us in
        self.assertIn(b'Invalid username or password', response.data)
        self.assertIn(b'login', response.request.path.encode())

if __name__ == '__main__':
    unittest.main()
