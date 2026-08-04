import unittest
from app import app
from database.db_connector import get_db_connection

class OmniScanXRenderTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # We need a valid DB connection to test rendering
        self.db_works = False
        try:
            conn = get_db_connection()
            if conn:
                self.db_works = True
                conn.close()
        except Exception:
            pass

    def test_database_connection(self):
        """Test if the PostgreSQL/Supabase database is reachable."""
        self.assertTrue(self.db_works, "Database Connection Failed")

    def test_public_routes(self):
        """Test public pages for rendering issues (500 errors)."""
        routes = ['/login', '/signup', '/verify_otp']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with status {response.status_code}")

    def test_admin_routes_rendering(self):
        """Test admin pages by mocking a session."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
            sess['role'] = 'admin'
            
        routes = [
            '/admin_dashboard',
            '/admin/student/add',
            '/admin/enroll_face',
            '/admin/auto_attendance',
            '/admin/attendance/report/weekly'
        ]
        
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Admin Route {route} failed with status {response.status_code}")
            
    def test_student_routes_rendering(self):
        """Test student pages by mocking a session."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['username'] = 'student'
            sess['role'] = 'student'
            
        routes = [
            '/student_dashboard'
        ]
        
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Student Route {route} failed with status {response.status_code}")

if __name__ == '__main__':
    unittest.main()
