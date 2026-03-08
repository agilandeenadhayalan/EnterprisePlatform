-- ==============================================
-- Smart Mobility & Analytics Platform
-- PostgreSQL Initialization Script
-- ==============================================
-- This runs automatically on first container start.
-- Creates schemas, extensions, and base tables for Phase 1.

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- Password hashing
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram text search

-- Create schemas for domain separation
CREATE SCHEMA IF NOT EXISTS identity;    -- Auth, sessions, devices
CREATE SCHEMA IF NOT EXISTS users;       -- User profiles, preferences
CREATE SCHEMA IF NOT EXISTS platform;    -- Config, feature flags, audit

-- ── Identity Domain ──

CREATE TABLE identity.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'rider',
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(512) NOT NULL,
    device_info JSONB,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    scopes TEXT[],
    rate_limit_per_minute INT DEFAULT 60,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Platform Domain ──

CREATE TABLE platform.audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    ip_address INET,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE platform.feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT FALSE,
    rollout_percentage INT DEFAULT 0,
    target_roles TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ──

CREATE INDEX idx_users_email ON identity.users(email);
CREATE INDEX idx_users_role ON identity.users(role);
CREATE INDEX idx_sessions_user_id ON identity.user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON identity.user_sessions(expires_at);
CREATE INDEX idx_audit_user_id ON platform.audit_log(user_id);
CREATE INDEX idx_audit_action ON platform.audit_log(action);
CREATE INDEX idx_audit_created ON platform.audit_log(created_at);

-- ── Seed admin user ──
-- Password: admin123 (bcrypt hash)
INSERT INTO identity.users (email, full_name, role, password_hash, is_active, is_verified)
VALUES (
    'admin@mobility.dev',
    'Platform Admin',
    'admin',
    '$2b$12$LJ3m5XkX3.qRjNdZ5Cj5aeYJ5GYXZ7u3/gYw7L5vH0G1Vp3F6.Ey',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- ── Report ──
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Smart Mobility Platform DB initialized!';
    RAISE NOTICE 'Schemas: identity, users, platform';
    RAISE NOTICE 'Tables: 5 created';
    RAISE NOTICE 'Admin: admin@mobility.dev';
    RAISE NOTICE '========================================';
END
$$;
