-- =====================================================================
-- Smart Campus Resource Booking System
-- database.sql
-- This script creates all the tables and adds test data.
-- It is run automatically by DatabaseManager the first time the
-- program starts (when campus_booking.db does not exist yet).
-- All test passwords are: password123 (stored as a SHA-256 hash)
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. ROLES table: the three types of users in the system
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT NOT NULL UNIQUE
);

-- ---------------------------------------------------------------------
-- 2. CAMPUSES table: each campus stores its OWN booking rules.
--    Adding a new campus only needs a new row here (no code changes).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campuses (
    campus_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    campus_name       TEXT NOT NULL UNIQUE,
    location          TEXT NOT NULL,
    max_hours         INTEGER NOT NULL,          -- longest booking allowed
    min_days_advance  INTEGER NOT NULL DEFAULT 0,-- how many days before you must book
    open_hour         INTEGER NOT NULL,          -- first hour bookings may start
    close_hour        INTEGER NOT NULL           -- bookings must end by this hour
);

-- ---------------------------------------------------------------------
-- 3. USERS table: every person who can log in
--    campus_id is only used for Campus Administrators (their campus)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    full_name      TEXT NOT NULL,
    email          TEXT NOT NULL,
    role_id        INTEGER NOT NULL,
    campus_id      INTEGER,
    FOREIGN KEY (role_id)   REFERENCES roles(role_id),
    FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
);

-- ---------------------------------------------------------------------
-- 4. RESOURCES table: labs, projectors, seminar rooms, etc.
--    resource_code is UNIQUE so duplicates are rejected.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS resources (
    resource_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_code  TEXT NOT NULL UNIQUE,
    resource_name  TEXT NOT NULL,
    resource_type  TEXT NOT NULL,
    capacity       INTEGER NOT NULL CHECK (capacity > 0),
    status         TEXT NOT NULL DEFAULT 'Available'
                   CHECK (status IN ('Available', 'Unavailable')),
    campus_id      INTEGER NOT NULL,
    FOREIGN KEY (campus_id) REFERENCES campuses(campus_id)
);

-- ---------------------------------------------------------------------
-- 5. BOOKINGS table: links a user, a resource and a campus
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    booking_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    resource_id     INTEGER NOT NULL,
    campus_id       INTEGER NOT NULL,
    booking_date    TEXT NOT NULL,              -- format YYYY-MM-DD
    start_time      TEXT NOT NULL,              -- format HH:MM
    duration_hours  INTEGER NOT NULL CHECK (duration_hours > 0),
    purpose         TEXT,
    status          TEXT NOT NULL DEFAULT 'Active'
                    CHECK (status IN ('Active', 'Cancelled')),
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(user_id),
    FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
    FOREIGN KEY (campus_id)   REFERENCES campuses(campus_id)
);

-- =====================================================================
-- TEST DATA
-- =====================================================================

INSERT INTO roles (role_name) VALUES
    ('Lecturer'),
    ('Campus Administrator'),
    ('System Operator');

-- Each campus has DIFFERENT rules
INSERT INTO campuses (campus_name, location, max_hours, min_days_advance, open_hour, close_hour) VALUES
    ('Johannesburg Campus', 'Braamfontein, Johannesburg', 4, 0, 8, 18),
    ('Durban Campus',       'Umhlanga, Durban',           6, 0, 7, 20),
    ('Cape Town Campus',    'Bellville, Cape Town',       5, 1, 8, 17);

-- password for everyone = password123
INSERT INTO users (username, password_hash, full_name, email, role_id, campus_id) VALUES
    ('operator',  'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Sipho Ndlovu',     'sipho.ndlovu@richfield.ac.za',  3, NULL),
    ('admin_jhb', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Lerato Molefe',    'lerato.molefe@richfield.ac.za', 2, 1),
    ('admin_dbn', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Ayanda Zulu',      'ayanda.zulu@richfield.ac.za',   2, 2),
    ('admin_cpt', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Megan Adams',      'megan.adams@richfield.ac.za',   2, 3),
    ('thabo',     'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Thabo Mokoena',    'thabo.mokoena@richfield.ac.za', 1, NULL),
    ('naledi',    'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Naledi Dlamini',   'naledi.dlamini@richfield.ac.za',1, NULL),
    ('johan',     'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'Johan van Wyk',    'johan.vanwyk@richfield.ac.za',  1, NULL);

INSERT INTO resources (resource_code, resource_name, resource_type, capacity, status, campus_id) VALUES
    ('JHB-LAB01',  'Computer Lab 1',       'Computer Lab',  40, 'Available',   1),
    ('JHB-LAB02',  'Computer Lab 2',       'Computer Lab',  30, 'Unavailable', 1),
    ('JHB-PROJ01', 'Epson Projector A',    'Projector',      1, 'Available',   1),
    ('JHB-SEM01',  'Seminar Room 101',     'Seminar Room',  25, 'Available',   1),
    ('DBN-LAB01',  'Computer Lab Alpha',   'Computer Lab',  35, 'Available',   2),
    ('DBN-PROJ01', 'BenQ Projector',       'Projector',      1, 'Available',   2),
    ('DBN-SEM01',  'Seminar Room Ocean',   'Seminar Room',  20, 'Available',   2),
    ('CPT-LAB01',  'Computer Lab Table',   'Computer Lab',  30, 'Available',   3),
    ('CPT-PROJ01', 'Sony Projector',       'Projector',      1, 'Available',   3),
    ('CPT-SEM01',  'Seminar Room Harbour', 'Seminar Room',  15, 'Available',   3),
    ('CPT-AV01',   'Presentation Kit',     'Presentation Equipment', 1, 'Available', 3);

-- Dates are relative to "today" so there are always past AND future bookings
INSERT INTO bookings (user_id, resource_id, campus_id, booking_date, start_time, duration_hours, purpose, status) VALUES
    (5, 1, 1, date('now', '-7 days'), '09:00', 2, 'Python practical',      'Active'),
    (5, 3, 1, date('now', '-3 days'), '13:00', 1, 'Lecture slides',        'Active'),
    (6, 1, 1, date('now', '-2 days'), '10:00', 3, 'Database test',         'Active'),
    (5, 1, 1, date('now', '+2 days'), '09:00', 2, 'Programming 512 class', 'Active'),
    (6, 4, 1, date('now', '+3 days'), '14:00', 2, 'Research seminar',      'Active'),
    (7, 5, 2, date('now', '-5 days'), '08:00', 5, 'Networking workshop',   'Active'),
    (7, 5, 2, date('now', '-1 days'), '12:00', 6, 'Exam preparation',      'Active'),
    (6, 7, 2, date('now', '+4 days'), '10:00', 4, 'Group presentations',   'Active'),
    (5, 6, 2, date('now', '+5 days'), '15:00', 2, 'Guest lecture',         'Cancelled'),
    (7, 8, 3, date('now', '-6 days'), '09:00', 3, 'Web development lab',   'Active'),
    (6, 10,3, date('now', '-4 days'), '11:00', 2, 'Tutorial session',      'Active'),
    (7, 8, 3, date('now', '+6 days'), '08:00', 4, 'Assessment',            'Active');
