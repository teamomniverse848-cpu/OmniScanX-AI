-- ===================================================
-- Cloud-Based Attendance Management System Database Schema (PostgreSQL / Supabase)
-- ===================================================

-- 1. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Students Table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    department_id INT NOT NULL,
    enrollment_date DATE NOT NULL,
    profile_picture TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- 4. Attendance Table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    marked_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, date),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (marked_by) REFERENCES users(id) ON DELETE RESTRICT
);

-- ===================================================
-- Indexes for Performance Optimization
-- ===================================================
CREATE INDEX IF NOT EXISTS idx_student_department ON students(department_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);

-- ===================================================
-- Initial Admin Account Seed
-- ===================================================
INSERT INTO users (username, email, password_hash, role) 
VALUES ('admin', 'admin@example.com', 'scrypt:32768:8:1$y6A0Jp1p7Wn9X5q3$4e5b97d83f3e2b2a1a1f0a2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f', 'admin')
ON CONFLICT (username) DO NOTHING;

-- ===================================================
-- Initial Departments Seed
-- ===================================================
INSERT INTO departments (name) VALUES 
('Computer Science'),
('Information Technology'),
('Data Science'),
('Software Engineering')
ON CONFLICT (name) DO NOTHING;

-- ===================================================
-- AI Attendance Module Tables
-- ===================================================

-- 5. Face Embeddings Table
CREATE TABLE IF NOT EXISTS face_embeddings (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL UNIQUE,
    embedding JSONB NOT NULL, -- Storing vector as JSON array of floats
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 6. Class Sessions Table (for AI bulk capture)
CREATE TABLE IF NOT EXISTS class_sessions (
    id SERIAL PRIMARY KEY,
    faculty_name VARCHAR(100) NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    batch VARCHAR(50) NOT NULL,
    section VARCHAR(50) NOT NULL,
    department_id INT NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- Add class_session_id to attendance if it doesn't exist
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_session_id INT;
ALTER TABLE attendance DROP CONSTRAINT IF EXISTS fk_class_session;
ALTER TABLE attendance ADD CONSTRAINT fk_class_session FOREIGN KEY (class_session_id) REFERENCES class_sessions(id) ON DELETE SET NULL;

-- ===================================================
-- Enable Row Level Security (RLS) to prevent public Data API access
-- ===================================================
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_sessions ENABLE ROW LEVEL SECURITY;
