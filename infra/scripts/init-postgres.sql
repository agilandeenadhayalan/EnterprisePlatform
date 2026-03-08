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

-- ══════════════════════════════════════════════
-- Phase 2: Event-Driven Architecture Tables
-- ══════════════════════════════════════════════

-- Enable PostGIS for geospatial queries
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create Phase 2 schemas
CREATE SCHEMA IF NOT EXISTS drivers;
CREATE SCHEMA IF NOT EXISTS trips;
CREATE SCHEMA IF NOT EXISTS vehicles;
CREATE SCHEMA IF NOT EXISTS dispatch;
CREATE SCHEMA IF NOT EXISTS pricing;
CREATE SCHEMA IF NOT EXISTS payments;
CREATE SCHEMA IF NOT EXISTS comms;
CREATE SCHEMA IF NOT EXISTS marketplace;

-- ── Driver Domain ──

CREATE TABLE drivers.drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    license_number VARCHAR(50) NOT NULL,
    license_expiry DATE,
    vehicle_id UUID,
    is_available BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    rating DECIMAL(3,2) DEFAULT 5.00,
    total_trips INT DEFAULT 0,
    acceptance_rate DECIMAL(5,2) DEFAULT 100.00,
    cancellation_rate DECIMAL(5,2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_locations (
    id BIGSERIAL PRIMARY KEY,
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    heading DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'offline',
    went_online_at TIMESTAMPTZ,
    went_offline_at TIMESTAMPTZ,
    shift_hours DECIMAL(4,2) DEFAULT 0,
    zone_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id) ON DELETE CASCADE,
    rider_id UUID NOT NULL REFERENCES identity.users(id),
    trip_id UUID NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    document_url VARCHAR(512),
    status VARCHAR(20) DEFAULT 'pending',
    verified_by UUID REFERENCES identity.users(id),
    verified_at TIMESTAMPTZ,
    expires_at DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_earnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id) ON DELETE CASCADE,
    trip_id UUID,
    amount DECIMAL(10,2) NOT NULL,
    earning_type VARCHAR(30) NOT NULL DEFAULT 'trip',
    description TEXT,
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE drivers.driver_incentives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    incentive_type VARCHAR(30) NOT NULL,
    target_trips INT,
    target_hours DECIMAL(4,2),
    bonus_amount DECIMAL(10,2),
    zone_id VARCHAR(50),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Vehicle Domain ──

CREATE TABLE vehicles.vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers.drivers(id) ON DELETE SET NULL,
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    year INT NOT NULL,
    color VARCHAR(30),
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    vehicle_type VARCHAR(30) NOT NULL DEFAULT 'sedan',
    capacity INT DEFAULT 4,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vehicles.vehicle_inspections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles.vehicles(id) ON DELETE CASCADE,
    inspector_id UUID REFERENCES identity.users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    inspection_type VARCHAR(30) NOT NULL,
    checklist JSONB DEFAULT '{}',
    notes TEXT,
    inspection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    next_due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vehicles.vehicle_maintenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles.vehicles(id) ON DELETE CASCADE,
    maintenance_type VARCHAR(50) NOT NULL,
    description TEXT,
    cost DECIMAL(10,2),
    mileage INT,
    performed_by VARCHAR(100),
    performed_at DATE NOT NULL DEFAULT CURRENT_DATE,
    next_due_date DATE,
    next_due_mileage INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE vehicles.vehicle_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    min_capacity INT DEFAULT 1,
    max_capacity INT DEFAULT 4,
    base_fare DECIMAL(10,2) NOT NULL,
    per_mile_rate DECIMAL(10,2) NOT NULL,
    per_minute_rate DECIMAL(10,2) NOT NULL,
    minimum_fare DECIMAL(10,2) NOT NULL,
    icon_url VARCHAR(512),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Trip Domain ──

CREATE TABLE trips.trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES identity.users(id),
    driver_id UUID REFERENCES drivers.drivers(id),
    vehicle_id UUID REFERENCES vehicles.vehicles(id),
    status VARCHAR(30) NOT NULL DEFAULT 'requested',
    pickup_latitude DOUBLE PRECISION NOT NULL,
    pickup_longitude DOUBLE PRECISION NOT NULL,
    pickup_address TEXT,
    dropoff_latitude DOUBLE PRECISION NOT NULL,
    dropoff_longitude DOUBLE PRECISION NOT NULL,
    dropoff_address TEXT,
    vehicle_type VARCHAR(30) DEFAULT 'economy',
    estimated_fare DECIMAL(10,2),
    actual_fare DECIMAL(10,2),
    distance_miles DECIMAL(10,2),
    duration_minutes DECIMAL(10,2),
    surge_multiplier DECIMAL(4,2) DEFAULT 1.00,
    payment_method VARCHAR(30) DEFAULT 'credit_card',
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    arrived_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    cancelled_by VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trips.ride_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips.trips(id),
    rider_id UUID NOT NULL REFERENCES identity.users(id),
    pickup_latitude DOUBLE PRECISION NOT NULL,
    pickup_longitude DOUBLE PRECISION NOT NULL,
    pickup_address TEXT,
    dropoff_latitude DOUBLE PRECISION NOT NULL,
    dropoff_longitude DOUBLE PRECISION NOT NULL,
    dropoff_address TEXT,
    vehicle_type VARCHAR(30) DEFAULT 'economy',
    payment_method VARCHAR(30) DEFAULT 'credit_card',
    estimated_fare DECIMAL(10,2),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trips.ride_tracking (
    id BIGSERIAL PRIMARY KEY,
    trip_id UUID NOT NULL REFERENCES trips.trips(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    speed DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trips.ride_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID UNIQUE NOT NULL REFERENCES trips.trips(id) ON DELETE CASCADE,
    rider_id UUID NOT NULL REFERENCES identity.users(id),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id),
    rider_rating INT CHECK (rider_rating BETWEEN 1 AND 5),
    driver_rating INT CHECK (driver_rating BETWEEN 1 AND 5),
    rider_comment TEXT,
    driver_comment TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Dispatch Domain ──

CREATE TABLE dispatch.dispatch_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips.trips(id),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    distance_to_pickup DECIMAL(10,2),
    eta_minutes DECIMAL(10,2),
    score DECIMAL(10,4),
    attempt_number INT DEFAULT 1,
    offered_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dispatch.dispatch_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    zone_type VARCHAR(30) NOT NULL DEFAULT 'city',
    boundary GEOMETRY(Polygon, 4326),
    demand_multiplier DECIMAL(4,2) DEFAULT 1.00,
    max_drivers INT,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Pricing Domain ──

CREATE TABLE pricing.pricing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_type VARCHAR(30) NOT NULL,
    zone_id UUID REFERENCES dispatch.dispatch_zones(id),
    base_fare DECIMAL(10,2) NOT NULL,
    per_mile_rate DECIMAL(10,2) NOT NULL,
    per_minute_rate DECIMAL(10,2) NOT NULL,
    minimum_fare DECIMAL(10,2) NOT NULL,
    booking_fee DECIMAL(10,2) DEFAULT 0,
    cancellation_fee DECIMAL(10,2) DEFAULT 5.00,
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pricing.surge_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID REFERENCES dispatch.dispatch_zones(id),
    surge_multiplier DECIMAL(4,2) NOT NULL DEFAULT 1.00,
    demand_count INT DEFAULT 0,
    supply_count INT DEFAULT 0,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pricing.discounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    max_discount DECIMAL(10,2),
    min_fare DECIMAL(10,2) DEFAULT 0,
    max_uses INT,
    current_uses INT DEFAULT 0,
    user_id UUID REFERENCES identity.users(id),
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pricing.promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    promotion_type VARCHAR(30) NOT NULL,
    discount_percentage DECIMAL(5,2),
    discount_amount DECIMAL(10,2),
    max_rides INT,
    target_audience TEXT[],
    zone_id UUID REFERENCES dispatch.dispatch_zones(id),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Payment Domain ──

CREATE TABLE payments.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips.trips(id),
    rider_id UUID NOT NULL REFERENCES identity.users(id),
    driver_id UUID REFERENCES drivers.drivers(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_method_id UUID,
    payment_method_type VARCHAR(30),
    transaction_id VARCHAR(255),
    breakdown JSONB DEFAULT '{}',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    method_type VARCHAR(30) NOT NULL,
    provider VARCHAR(50),
    last_four VARCHAR(4),
    expiry_month INT,
    expiry_year INT,
    token_encrypted VARCHAR(512),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments.payments(id),
    amount DECIMAL(10,2) NOT NULL,
    reason VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by UUID REFERENCES identity.users(id),
    transaction_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE payments.payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID NOT NULL REFERENCES drivers.drivers(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payout_method VARCHAR(30),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    trip_count INT DEFAULT 0,
    transaction_id VARCHAR(255),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES payments.wallets(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    reference_id UUID,
    description TEXT,
    balance_after DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.fare_splits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips.trips(id),
    initiator_id UUID NOT NULL REFERENCES identity.users(id),
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE payments.fare_split_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    split_id UUID NOT NULL REFERENCES payments.fare_splits(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES identity.users(id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Communication Domain ──

CREATE TABLE comms.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    notification_type VARCHAR(30) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'push',
    reference_type VARCHAR(50),
    reference_id UUID,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE comms.chat_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips.trips(id),
    room_type VARCHAR(20) NOT NULL DEFAULT 'trip',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE comms.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES comms.chat_rooms(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES identity.users(id),
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Marketplace Domain ──

CREATE TABLE marketplace.loyalty_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    points INT NOT NULL DEFAULT 0,
    lifetime_points INT NOT NULL DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'bronze',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE marketplace.loyalty_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id),
    points INT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    reference_type VARCHAR(50),
    reference_id UUID,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE marketplace.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id) ON DELETE CASCADE,
    plan_name VARCHAR(50) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    features JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE marketplace.support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(id),
    trip_id UUID REFERENCES trips.trips(id),
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    assigned_to UUID REFERENCES identity.users(id),
    resolution TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- ── Phase 2 Indexes ──

CREATE INDEX idx_drivers_user_id ON drivers.drivers(user_id);
CREATE INDEX idx_drivers_available ON drivers.drivers(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_driver_locations_driver ON drivers.driver_locations(driver_id);
CREATE INDEX idx_driver_locations_time ON drivers.driver_locations(recorded_at DESC);
CREATE INDEX idx_driver_locations_geom ON drivers.driver_locations USING GIST(geom);
CREATE INDEX idx_driver_ratings_driver ON drivers.driver_ratings(driver_id);
CREATE INDEX idx_driver_earnings_driver ON drivers.driver_earnings(driver_id);
CREATE INDEX idx_driver_earnings_period ON drivers.driver_earnings(period_start, period_end);

CREATE INDEX idx_trips_rider ON trips.trips(rider_id);
CREATE INDEX idx_trips_driver ON trips.trips(driver_id);
CREATE INDEX idx_trips_status ON trips.trips(status);
CREATE INDEX idx_trips_requested ON trips.trips(requested_at DESC);
CREATE INDEX idx_ride_requests_rider ON trips.ride_requests(rider_id);
CREATE INDEX idx_ride_requests_status ON trips.ride_requests(status);
CREATE INDEX idx_ride_tracking_trip ON trips.ride_tracking(trip_id);
CREATE INDEX idx_ride_tracking_geom ON trips.ride_tracking USING GIST(geom);

CREATE INDEX idx_vehicles_driver ON vehicles.vehicles(driver_id);
CREATE INDEX idx_vehicles_type ON vehicles.vehicles(vehicle_type);

CREATE INDEX idx_dispatch_trip ON dispatch.dispatch_assignments(trip_id);
CREATE INDEX idx_dispatch_driver ON dispatch.dispatch_assignments(driver_id);
CREATE INDEX idx_dispatch_status ON dispatch.dispatch_assignments(status);
CREATE INDEX idx_dispatch_zones_geom ON dispatch.dispatch_zones USING GIST(boundary);

CREATE INDEX idx_pricing_rules_type ON pricing.pricing_rules(vehicle_type);
CREATE INDEX idx_surge_zones_zone ON pricing.surge_zones(zone_id);
CREATE INDEX idx_discounts_code ON pricing.discounts(code);
CREATE INDEX idx_discounts_user ON pricing.discounts(user_id);

CREATE INDEX idx_payments_trip ON payments.payments(trip_id);
CREATE INDEX idx_payments_rider ON payments.payments(rider_id);
CREATE INDEX idx_payments_status ON payments.payments(status);
CREATE INDEX idx_payment_methods_user ON payments.payment_methods(user_id);
CREATE INDEX idx_payouts_driver ON payments.payouts(driver_id);
CREATE INDEX idx_payouts_period ON payments.payouts(period_start, period_end);
CREATE INDEX idx_wallets_user ON payments.wallets(user_id);
CREATE INDEX idx_wallet_txn_wallet ON payments.wallet_transactions(wallet_id);

CREATE INDEX idx_notifications_user ON comms.notifications(user_id);
CREATE INDEX idx_notifications_unread ON comms.notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_chat_messages_room ON comms.chat_messages(room_id);
CREATE INDEX idx_chat_rooms_trip ON comms.chat_rooms(trip_id);

CREATE INDEX idx_loyalty_user ON marketplace.loyalty_points(user_id);
CREATE INDEX idx_subscriptions_user ON marketplace.subscriptions(user_id);
CREATE INDEX idx_support_tickets_user ON marketplace.support_tickets(user_id);
CREATE INDEX idx_support_tickets_status ON marketplace.support_tickets(status);

-- ── Phase 2 Seed Data ──

INSERT INTO vehicles.vehicle_types (name, display_name, description, min_capacity, max_capacity, base_fare, per_mile_rate, per_minute_rate, minimum_fare) VALUES
    ('economy', 'Economy', 'Affordable rides for everyday trips', 1, 4, 2.50, 1.25, 0.20, 7.00),
    ('comfort', 'Comfort', 'Newer cars with extra legroom', 1, 4, 3.50, 1.75, 0.30, 10.00),
    ('premium', 'Premium', 'Luxury vehicles with top-rated drivers', 1, 4, 5.00, 2.50, 0.45, 15.00),
    ('xl', 'XL', 'Spacious rides for groups up to 6', 1, 6, 4.00, 2.00, 0.35, 12.00),
    ('luxury', 'Luxury', 'High-end vehicles for special occasions', 1, 4, 8.00, 3.50, 0.60, 25.00)
ON CONFLICT (name) DO NOTHING;

INSERT INTO pricing.pricing_rules (vehicle_type, base_fare, per_mile_rate, per_minute_rate, minimum_fare, booking_fee) VALUES
    ('economy', 2.50, 1.25, 0.20, 7.00, 1.99),
    ('comfort', 3.50, 1.75, 0.30, 10.00, 2.49),
    ('premium', 5.00, 2.50, 0.45, 15.00, 3.49),
    ('xl', 4.00, 2.00, 0.35, 12.00, 2.99),
    ('luxury', 8.00, 3.50, 0.60, 25.00, 4.99);

-- ── Report ──
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Smart Mobility Platform DB initialized!';
    RAISE NOTICE 'Schemas: identity, users, platform,';
    RAISE NOTICE '  drivers, trips, vehicles, dispatch,';
    RAISE NOTICE '  pricing, payments, comms, marketplace';
    RAISE NOTICE 'Phase 1 Tables: 17';
    RAISE NOTICE 'Phase 2 Tables: 30+';
    RAISE NOTICE 'Roles: rider, driver, admin, support';
    RAISE NOTICE 'Admin: admin@mobility.dev';
    RAISE NOTICE '========================================';
END
$$;
