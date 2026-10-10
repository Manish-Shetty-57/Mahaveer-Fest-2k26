-- ============================================================================
-- MAHAVEERA FEST 2K26 - PostgreSQL Production Database Schema
-- Sri Mahaveera College, Kodangallu - 574197, Moodbidri, D.K. District
-- Event Date: 30 October 2026 | Deadline: 24 October 2026 23:59:59 IST
-- ============================================================================

-- 1. Enable UUID Extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Custom ENUM Types
DO $$ BEGIN
    CREATE TYPE puc_year_enum AS ENUM ('1st PUC', '2nd PUC');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE department_enum AS ENUM ('SCIENCE', 'COMMERCE', 'IT', 'HUMANITIES');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Colleges Table
-- Stores participating institutions and coordinator credentials.
-- total_students_registered tracks the count of distinct students registered across all events.
CREATE TABLE IF NOT EXISTS colleges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    college_name VARCHAR(255) NOT NULL,
    faculty_coordinator_name VARCHAR(255) NOT NULL,
    faculty_phone VARCHAR(20) NOT NULL,
    faculty_email VARCHAR(255) NOT NULL,
    total_students_registered INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Rule 1 Constraint: Maximum 25 unique students cap enforced at schema level
    CONSTRAINT chk_college_student_cap CHECK (total_students_registered >= 0 AND total_students_registered <= 25),
    CONSTRAINT uq_colleges_college_name UNIQUE (college_name)
);

-- Indexing for fast lookups
CREATE INDEX IF NOT EXISTS idx_colleges_name_lower ON colleges (LOWER(college_name));
CREATE INDEX IF NOT EXISTS idx_colleges_email ON colleges (faculty_email);

-- 4. Students Table
-- Stores individual PU student details linked to their college.
CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    college_id UUID NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    puc_year puc_year_enum NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_students_college 
        FOREIGN KEY (college_id) 
        REFERENCES colleges(id) 
        ON DELETE CASCADE,

    -- Prevent duplicate identical student entries within the same college
    CONSTRAINT uq_student_per_college UNIQUE (college_id, student_name, puc_year)
);

CREATE INDEX IF NOT EXISTS idx_students_college_id ON students (college_id);
CREATE INDEX IF NOT EXISTS idx_students_name_puc ON students (LOWER(student_name), puc_year);

-- 5. Registrations Table
-- Records event enrollments per college.
CREATE TABLE IF NOT EXISTS registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    college_id UUID NOT NULL,
    event_name VARCHAR(100) NOT NULL,
    department department_enum NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_registrations_college 
        FOREIGN KEY (college_id) 
        REFERENCES colleges(id) 
        ON DELETE CASCADE,

    -- General Rule: Only one team per college is allowed per event
    CONSTRAINT uq_college_event_single_team UNIQUE (college_id, event_name)
);

CREATE INDEX IF NOT EXISTS idx_registrations_college ON registrations (college_id);
CREATE INDEX IF NOT EXISTS idx_registrations_dept ON registrations (department);
CREATE INDEX IF NOT EXISTS idx_registrations_event ON registrations (event_name);

-- 6. Registration Members Junction Table
-- Implements the Many-to-Many relationship between Registrations and participating Students.
-- In relational Postgres, this models the "team_members (Array of student IDs)" with full referential integrity.
CREATE TABLE IF NOT EXISTS registration_members (
    registration_id UUID NOT NULL,
    student_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (registration_id, student_id),

    CONSTRAINT fk_reg_members_registration 
        FOREIGN KEY (registration_id) 
        REFERENCES registrations(id) 
        ON DELETE CASCADE,

    CONSTRAINT fk_reg_members_student 
        FOREIGN KEY (student_id) 
        REFERENCES students(id) 
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_reg_members_student ON registration_members (student_id);
CREATE INDEX IF NOT EXISTS idx_reg_members_registration ON registration_members (registration_id);

-- 7. Automated Database Trigger: Recalculate and Enforce 25 Unique Student Cap
-- Provides defense-in-depth at the PostgreSQL storage engine level.
CREATE OR REPLACE FUNCTION fn_sync_college_unique_students()
RETURNS TRIGGER AS $$
DECLARE
    v_college_id UUID;
    v_unique_count INT;
BEGIN
    -- Determine affected college
    IF TG_OP = 'DELETE' THEN
        SELECT college_id INTO v_college_id FROM registrations WHERE id = OLD.registration_id;
    ELSE
        SELECT college_id INTO v_college_id FROM registrations WHERE id = NEW.registration_id;
    END IF;

    IF v_college_id IS NOT NULL THEN
        -- Calculate distinct students enrolled in any event for this college
        SELECT COUNT(DISTINCT rm.student_id) INTO v_unique_count
        FROM registration_members rm
        JOIN registrations r ON rm.registration_id = r.id
        WHERE r.college_id = v_college_id;

        -- Check 25-Student College Cap
        IF v_unique_count > 25 THEN
            RAISE EXCEPTION 'Rule 1 Violation: College % exceeds the maximum limit of 25 unique students (Attempted: %)',
                v_college_id, v_unique_count
                USING ERRCODE = 'check_violation';
        END IF;

        -- Synchronize total_students_registered counter
        UPDATE colleges
        SET total_students_registered = v_unique_count,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = v_college_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_unique_students_insert ON registration_members;
CREATE TRIGGER trg_sync_unique_students_insert
    AFTER INSERT OR UPDATE OR DELETE ON registration_members
    FOR EACH ROW
    EXECUTE FUNCTION fn_sync_college_unique_students();
