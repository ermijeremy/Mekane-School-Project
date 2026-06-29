-- USERS & AUTH

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    role          VARCHAR(20)  NOT NULL CHECK (role IN ('admin', 'teacher', 'student')),
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- SCHOOL INFO

-- CREATE TABLE school_info (
--     id                INT PRIMARY KEY DEFAULT 1,  -- singleton row
--     name              VARCHAR(255) NOT NULL,
--     logo_url          VARCHAR(500),
--     address           TEXT,
--     phone             VARCHAR(50),
--     email             VARCHAR(255),
--     website           VARCHAR(255),
--     principal_name    VARCHAR(255),
--     principal_message TEXT,
--     established_year  INT,
--     map_embed_url     VARCHAR(500),
--     updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     CONSTRAINT school_info_singleton CHECK (id = 1)
-- );


-- ACADEMIC STRUCTURE

CREATE TABLE academic_years (
    id         BIGSERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,  -- e.g. '2024-2025 Semester 1'
    start_date DATE         NOT NULL,
    end_date   DATE         NOT NULL,
    is_current BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Teachers table declared before classes because classes.homeroom_teacher_id references it
CREATE TABLE teachers (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT       NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    full_name  VARCHAR(255) NOT NULL,
    phone      VARCHAR(50),
    photo_url  VARCHAR(500),
    is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Class rooms
CREATE TABLE classes (
    id                  BIGSERIAL PRIMARY KEY,
    academic_year_id    BIGINT      NOT NULL REFERENCES academic_years(id) ON DELETE RESTRICT,
    grade_level         INT         NOT NULL,   -- e.g. 9, 10, 11, 12
    section             VARCHAR(50) NOT NULL,   -- e.g. 'A', 'B', 'C'
    homeroom_teacher_id BIGINT      REFERENCES teachers(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (academic_year_id, grade_level, section)
);

CREATE TABLE subjects (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Which teacher teaches which subject in which class
CREATE TABLE class_subject_teachers (
    id         BIGSERIAL PRIMARY KEY,
    class_id   BIGINT NOT NULL REFERENCES classes(id)   ON DELETE CASCADE,
    subject_id BIGINT NOT NULL REFERENCES subjects(id)  ON DELETE RESTRICT,
    teacher_id BIGINT NOT NULL REFERENCES teachers(id)  ON DELETE RESTRICT,
    UNIQUE (class_id, subject_id)
);


-- PEOPLE

CREATE TABLE admins (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT       NOT NULL UNIQUE REFERENCES users(id) ON DELETE RESTRICT,
    first_name VARCHAR(255) NOT NULL,
    last_name  VARCHAR(255) NOT NULL,
    phone      VARCHAR(50),
    photo_url  VARCHAR(500),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE students (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT      UNIQUE REFERENCES users(id) ON DELETE SET NULL,  -- null until approved
    student_id_number VARCHAR(50) UNIQUE,  -- auto-generated on approval
    first_name        VARCHAR(255) NOT NULL,
    last_name         VARCHAR(255) NOT NULL,
    date_of_birth     DATE,
    gender            VARCHAR(20)  CHECK (gender IN ('male', 'female')),
    phone             VARCHAR(50),
    photo_url         VARCHAR(500),
    address           TEXT,
    current_class_id  BIGINT      REFERENCES classes(id) ON DELETE SET NULL,
    academic_status   VARCHAR(50)  NOT NULL DEFAULT 'active'
                          CHECK (academic_status IN ('active', 'suspended', 'graduated', 'withdrawn')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Enrollment history across academic years (promotions, transfers)
CREATE TABLE enrollments (
    id               BIGSERIAL PRIMARY KEY,
    student_id       BIGINT      NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    class_id         BIGINT      NOT NULL REFERENCES classes(id)  ON DELETE RESTRICT,
    academic_year_id BIGINT      NOT NULL REFERENCES academic_years(id) ON DELETE RESTRICT,
    enrolled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status           VARCHAR(30)  NOT NULL DEFAULT 'active'
                         CHECK (status IN ('active', 'transferred', 'promoted', 'withdrawn')),
    UNIQUE (student_id, academic_year_id)
);


-- STUDENT REGISTRATION WORKFLOW

CREATE TABLE registration_applications (
    id                   BIGSERIAL PRIMARY KEY,
    -- Applicant info
    full_name            VARCHAR(255) NOT NULL,
    date_of_birth        DATE,
    gender               VARCHAR(20)  CHECK (gender IN ('male', 'female')),
    address              TEXT,
    phone                VARCHAR(50),
    email                VARCHAR(255),
    photo_url            VARCHAR(500),
    grade_level          INT          NOT NULL,
    academic_year_id     BIGINT       REFERENCES academic_years(id) ON DELETE SET NULL,
    -- Guardian
    guardian_name        VARCHAR(255),
    guardian_relation    VARCHAR(50),
    guardian_phone       VARCHAR(50),
    guardian_email       VARCHAR(255),
    -- Workflow
    status               VARCHAR(30)  NOT NULL DEFAULT 'pending_review'
                             CHECK (status IN (
                                 'pending_review', 'approved', 'rejected',
                                 'waiting_for_payment', 'registered'
                             )),
    rejection_reason     TEXT,
    payment_received_at  TIMESTAMPTZ,
    payment_amount       NUMERIC(10, 2),
    reviewed_by          BIGINT       REFERENCES admins(id) ON DELETE SET NULL,
    reviewed_at          TIMESTAMPTZ,
    converted_student_id BIGINT       REFERENCES students(id) ON DELETE SET NULL,
    submitted_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE registration_documents (
    id             BIGSERIAL PRIMARY KEY,
    application_id BIGINT       NOT NULL REFERENCES registration_applications(id) ON DELETE CASCADE,
    document_type  VARCHAR(100) NOT NULL
                       CHECK (document_type IN ('birth_certificate', 'transcript', 'photo', 'other')),
    file_url       VARCHAR(500) NOT NULL,
    file_name      VARCHAR(255),
    description    TEXT,
    uploaded_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- ATTENDANCE

-- Recorded once per student per day by the class homeroom teacher
CREATE TABLE attendance_records (
    id          BIGSERIAL PRIMARY KEY,
    student_id  BIGINT      NOT NULL REFERENCES students(id)  ON DELETE CASCADE,
    class_id    BIGINT      NOT NULL REFERENCES classes(id)   ON DELETE RESTRICT,
    date        DATE        NOT NULL,
    status      VARCHAR(20) NOT NULL CHECK (status IN ('present', 'absent', 'late', 'excused')),
    recorded_by BIGINT      NOT NULL REFERENCES teachers(id)  ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_id, date)
);


-- ASSESSMENTS & GRADES

CREATE TABLE assessments (
    id                       BIGSERIAL PRIMARY KEY,
    class_subject_teacher_id BIGINT       NOT NULL REFERENCES class_subject_teachers(id) ON DELETE RESTRICT,
    academic_year_id         BIGINT       NOT NULL REFERENCES academic_years(id)         ON DELETE RESTRICT,
    title                    VARCHAR(255) NOT NULL,
    type                     VARCHAR(30)  NOT NULL
                                 CHECK (type IN ('quiz', 'midterm', 'final', 'project', 'other')),
    max_score                NUMERIC(5, 2) NOT NULL DEFAULT 100,
    date                     DATE,
    is_published             BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at               TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE assessment_scores (
    id            BIGSERIAL PRIMARY KEY,
    assessment_id BIGINT        NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    student_id    BIGINT        NOT NULL REFERENCES students(id)    ON DELETE CASCADE,
    score         NUMERIC(5, 2) NOT NULL,
    note          TEXT,
    recorded_by   BIGINT        NOT NULL REFERENCES teachers(id)    ON DELETE RESTRICT,
    recorded_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (assessment_id, student_id)
);


-- ANNOUNCEMENTS

CREATE TABLE announcements (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    body            TEXT         NOT NULL,
    type            VARCHAR(30)  NOT NULL
                        CHECK (type IN ('school_wide', 'class', 'emergency', 'exam_schedule')),
    target_class_id BIGINT       REFERENCES classes(id) ON DELETE SET NULL,  -- null = school-wide
    published_by    BIGINT       NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    is_published    BOOLEAN      NOT NULL DEFAULT FALSE,
    is_pinned       BOOLEAN      NOT NULL DEFAULT FALSE,
    is_public       BOOLEAN      NOT NULL DEFAULT FALSE,  -- visible on public website
    scheduled_at    TIMESTAMPTZ,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- NOTIFICATIONS

CREATE TABLE notifications (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sender_id      BIGINT       REFERENCES users(id) ON DELETE SET NULL,  -- null = system generated
    type           VARCHAR(50)  NOT NULL
                       CHECK (type IN (
                           'announcement', 'attendance', 'grade_published',
                           'warning', 'academic_notice', 'registration', 'payment', 'system'
                       )),
    title          VARCHAR(255) NOT NULL,
    body           TEXT,
    reference_type VARCHAR(50)
                       CHECK (reference_type IN (
                           'announcement', 'assessment', 'attendance_record', 'registration_application'
                       )),
    reference_id   BIGINT,      -- logical FK to the relevant table row
    is_read        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);


-- PUBLIC WEBSITE

CREATE TABLE contact_inquiries (
    id           BIGSERIAL PRIMARY KEY,
    full_name    VARCHAR(255) NOT NULL,
    email        VARCHAR(255) NOT NULL,
    phone        VARCHAR(50),
    subject      VARCHAR(255),
    message      TEXT         NOT NULL,
    is_resolved  BOOLEAN      NOT NULL DEFAULT FALSE,
    resolved_by  BIGINT       REFERENCES admins(id) ON DELETE SET NULL,
    submitted_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE staff_profiles (
    id          BIGSERIAL PRIMARY KEY,
    first_name  VARCHAR(255) NOT NULL,
    last_name   VARCHAR(255) NOT NULL,
    role_title  VARCHAR(100),
    bio         TEXT,
    photo_url   VARCHAR(500),
    order_index INT          NOT NULL DEFAULT 0,
    is_visible  BOOLEAN      NOT NULL DEFAULT TRUE
);