-- APS Database Schema

CREATE DATABASE IF NOT EXISTS aps_db;
USE aps_db;

-- Users Table
CREATE TABLE IF NOT EXISTS User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role ENUM('student', 'supervisor', 'admin') NOT NULL
);

-- Student Table
CREATE TABLE IF NOT EXISTS Student (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    student_no VARCHAR(20) NOT NULL UNIQUE,
    department VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

-- Supervisor Table
CREATE TABLE IF NOT EXISTS Supervisor (
    supervisor_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(50),
    expertise VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

-- Admin Table (Optional, or just use User role)
-- For now, we rely on User.role = 'admin'

-- Project Table
CREATE TABLE IF NOT EXISTS Project (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status ENUM('active', 'completed', 'archived') DEFAULT 'active',
    supervisor_id INT NOT NULL,
    FOREIGN KEY (supervisor_id) REFERENCES Supervisor(supervisor_id) ON DELETE CASCADE
);

-- Selection (Student selects Project)
CREATE TABLE IF NOT EXISTS Selection (
    selection_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    project_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES Project(project_id) ON DELETE CASCADE
);

-- Task Table
CREATE TABLE IF NOT EXISTS Task (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    instruction TEXT,
    deadline DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Project(project_id) ON DELETE CASCADE
);

-- Submission Table
CREATE TABLE IF NOT EXISTS Submission (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    student_id INT NOT NULL,
    file_path VARCHAR(255),
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES Task(task_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE
);

-- Evaluation Table
CREATE TABLE IF NOT EXISTS Evaluation (
    evaluation_id INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT NOT NULL,
    grade INT CHECK (grade >= 0 AND grade <= 100),
    feedback TEXT,
    evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES Submission(submission_id) ON DELETE CASCADE
);

-- Notification Table
CREATE TABLE IF NOT EXISTS Notification (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(100),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

-- Activity Log Table
CREATE TABLE IF NOT EXISTS Activity_Log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type VARCHAR(50),
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE SET NULL
);
