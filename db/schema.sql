-- Esquema de la base de datos de Crea (PostgreSQL 13+)

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    timezone      VARCHAR(50)  NOT NULL DEFAULT 'America/Buenos_Aires',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE habits (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name          VARCHAR(100) NOT NULL,
    category      VARCHAR(20)  NOT NULL
        CHECK (category IN ('EXERCISE','READING','SAVINGS','MEDITATION','OTHER')),
    days_of_week  SMALLINT     NOT NULL CHECK (days_of_week BETWEEN 1 AND 127),
    reminder_time TIME,
    active        BOOLEAN      NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE habit_logs (
    id            UUID PRIMARY KEY,  -- lo genera el celular
    habit_id      UUID NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    log_date      DATE NOT NULL,
    completed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_habit_day UNIQUE (habit_id, log_date)
);

CREATE TABLE cities (
    user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bricks             INT  NOT NULL DEFAULT 0,
    current_streak     INT  NOT NULL DEFAULT 0,
    best_streak        INT  NOT NULL DEFAULT 0,
    last_completed_day DATE
);

CREATE TABLE buildings (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type      VARCHAR(20) NOT NULL
        CHECK (type IN ('HOUSE','GYM','LIBRARY','BANK','PARK','TOWER','SKYSCRAPER')),
    x         INT  NOT NULL,
    y         INT  NOT NULL,
    built_on  DATE NOT NULL,
    CONSTRAINT uq_building_position UNIQUE (user_id, x, y)
);

CREATE INDEX ix_habits_user ON habits(user_id);
CREATE INDEX ix_logs_date ON habit_logs(log_date);
CREATE INDEX ix_buildings_timeline ON buildings(user_id, built_on);
