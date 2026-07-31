-- MySQL setup script for ResumeScreen AI
-- Run as a user with CREATE DATABASE privileges

CREATE DATABASE IF NOT EXISTS resume_screening
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Optional: create a dedicated app user
-- CREATE USER IF NOT EXISTS 'resume_app'@'localhost' IDENTIFIED BY 'your_secure_password';
-- GRANT ALL PRIVILEGES ON resume_screening.* TO 'resume_app'@'localhost';
-- FLUSH PRIVILEGES;
