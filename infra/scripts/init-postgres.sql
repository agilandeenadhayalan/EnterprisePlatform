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

-- ── Identity Domain (continued) ──

CREATE TABLE identity.otp_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    code_hash VARCHAR(255) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'email',  -- email, sms
    purpose VARCHAR(50) NOT NULL DEFAULT 'verification',  -- verification, login, password_reset
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity.devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    fingerprint VARCHAR(512),
    device_name VARCHAR(255),
    device_type VARCHAR(50),   -- mobile, desktop, tablet
    os VARCHAR(100),
    browser VARCHAR(100),
    is_trusted BOOLEAN DEFAULT FALSE,
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, device_id)
);

CREATE TABLE identity.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '[]',
    is_system BOOLEAN DEFAULT FALSE,  -- System roles can't be deleted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity.user_roles (
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES identity.roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES identity.users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE identity.sso_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) UNIQUE NOT NULL,  -- google, github, microsoft
    client_id VARCHAR(255) NOT NULL,
    client_secret_encrypted VARCHAR(512),
    authorization_url VARCHAR(512),
    token_url VARCHAR(512),
    userinfo_url VARCHAR(512),
    scopes TEXT[] DEFAULT '{"openid", "email", "profile"}',
    is_enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity.sso_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES identity.sso_providers(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    external_email VARCHAR(255),
    access_token_encrypted VARCHAR(1024),
    refresh_token_encrypted VARCHAR(1024),
    token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider_id, external_id)
);

-- ── Users Domain ──

CREATE TABLE users.profiles (
    user_id UUID PRIMARY KEY REFERENCES identity.users(id) ON DELETE CASCADE,
    avatar_url VARCHAR(512),
    bio TEXT,
    date_of_birth DATE,
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    label VARCHAR(50) NOT NULL DEFAULT 'home',  -- home, work, other
    line1 VARCHAR(255) NOT NULL,
    line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'US',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.activity_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users.preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, category, key)
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

CREATE TABLE platform.configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    version INT DEFAULT 1,
    updated_by UUID REFERENCES identity.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service, key)
);

CREATE TABLE platform.flag_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flag_id UUID REFERENCES platform.feature_flags(id) ON DELETE CASCADE,
    user_id UUID REFERENCES identity.users(id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(flag_id, user_id)
);

-- ── Indexes ──

CREATE INDEX idx_users_email ON identity.users(email);
CREATE INDEX idx_users_role ON identity.users(role);
CREATE INDEX idx_sessions_user_id ON identity.user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON identity.user_sessions(expires_at);
CREATE INDEX idx_audit_user_id ON platform.audit_log(user_id);
CREATE INDEX idx_audit_action ON platform.audit_log(action);
CREATE INDEX idx_audit_created ON platform.audit_log(created_at);

-- New Phase 1 indexes
CREATE INDEX idx_otp_user_id ON identity.otp_codes(user_id);
CREATE INDEX idx_otp_expires ON identity.otp_codes(expires_at);
CREATE INDEX idx_devices_user_id ON identity.devices(user_id);
CREATE INDEX idx_devices_device_id ON identity.devices(device_id);
CREATE INDEX idx_user_roles_user ON identity.user_roles(user_id);
CREATE INDEX idx_sso_connections_user ON identity.sso_connections(user_id);
CREATE INDEX idx_addresses_user_id ON users.addresses(user_id);
CREATE INDEX idx_activity_user_id ON users.activity_log(user_id);
CREATE INDEX idx_activity_created ON users.activity_log(created_at);
CREATE INDEX idx_preferences_user_id ON users.preferences(user_id);
CREATE INDEX idx_configurations_service ON platform.configurations(service);
CREATE INDEX idx_flag_overrides_flag ON platform.flag_overrides(flag_id);
CREATE INDEX idx_flag_overrides_user ON platform.flag_overrides(user_id);

-- ── Seed Data ──

-- Seed admin user ──
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

-- Seed default RBAC roles
INSERT INTO identity.roles (name, description, permissions, is_system) VALUES
    ('rider', 'Standard rider', '["ride:create", "ride:read", "profile:read", "profile:write"]', TRUE),
    ('driver', 'Verified driver', '["ride:accept", "ride:update", "location:write", "earnings:read"]', TRUE),
    ('admin', 'Platform admin', '["*"]', TRUE),
    ('support', 'Customer support', '["user:read", "ride:read", "ride:update", "ticket:*"]', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Seed default configurations
INSERT INTO platform.configurations (service, key, value, description) VALUES
    ('auth-service', 'jwt_access_token_ttl_minutes', '15', 'Access token lifetime'),
    ('auth-service', 'jwt_refresh_token_ttl_days', '7', 'Refresh token lifetime'),
    ('auth-service', 'max_login_attempts', '5', 'Lockout threshold'),
    ('otp-service', 'otp_ttl_minutes', '10', 'OTP expiration time'),
    ('otp-service', 'otp_length', '6', 'Number of digits in OTP'),
    ('feature-flag-service', 'cache_ttl_seconds', '60', 'Flag evaluation cache TTL')
ON CONFLICT (service, key) DO NOTHING;

-- Seed sample feature flags
INSERT INTO platform.feature_flags (flag_name, description, is_enabled, rollout_percentage, target_roles) VALUES
    ('dark_mode', 'Enable dark mode UI', TRUE, 100, '{"rider", "driver", "admin"}'),
    ('new_pricing_model', 'Experimental dynamic pricing', FALSE, 10, '{"rider"}'),
    ('driver_tips', 'Enable in-app tipping', TRUE, 100, '{"rider", "driver"}')
ON CONFLICT (flag_name) DO NOTHING;

-- ── Report ──
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Smart Mobility Platform DB initialized!';
    RAISE NOTICE 'Schemas: identity, users, platform';
    RAISE NOTICE 'Tables: 17 created';
    RAISE NOTICE 'Roles: rider, driver, admin, support';
    RAISE NOTICE 'Admin: admin@mobility.dev';
    RAISE NOTICE '========================================';
END
$$;
