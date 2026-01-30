-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- Enable RLS extension
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 1. Create a helper function to extract tenant_id from the JWT
CREATE OR REPLACE FUNCTION auth.tenant_id() 
RETURNS TEXT AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true)::json->>'tenant_id', '')::TEXT;
$$ LANGUAGE sql STABLE;

-- 2. Apply Policy to Properties
-- This policy ensures users can only access properties that belong to their own tenant.
CREATE POLICY tenant_property_isolation ON properties
    FOR ALL
    TO authenticated
    USING (tenant_id = auth.tenant_id())
    WITH CHECK (tenant_id = auth.tenant_id());

-- 3. Apply Policy to Reservations
CREATE POLICY tenant_reservation_isolation ON reservations
    FOR ALL
    TO authenticated
    USING (tenant_id = auth.tenant_id())
    WITH CHECK (tenant_id = auth.tenant_id());

-- 4. Apply Policy to Tenants
-- Users should only be able to see their own tenant record
CREATE POLICY tenant_self_isolation ON tenants
    FOR SELECT
    TO authenticated
    USING (id = auth.tenant_id());

-- Tenants Table
CREATE TABLE tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Properties Table
CREATE TABLE properties (
    id TEXT NOT NULL, -- Not PK solely, might be composite with tenant in real world, but strict ID here
    tenant_id TEXT REFERENCES tenants(id),
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, tenant_id)
);

-- Reservations Table
CREATE TABLE reservations (
    id TEXT PRIMARY KEY,
    property_id TEXT,
    tenant_id TEXT REFERENCES tenants(id),
    check_in_date TIMESTAMP WITH TIME ZONE NOT NULL,
    check_out_date TIMESTAMP WITH TIME ZONE NOT NULL,
    total_amount NUMERIC(10, 3) NOT NULL, -- storing as numeric with 3 decimals to allow sub-cent precision tracking
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (property_id, tenant_id) REFERENCES properties(id, tenant_id)
);

-- RLS Policies (Simulation)
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE reservations ENABLE ROW LEVEL SECURITY;

-- Note: In a real Supabase setup, we'd have auth.uid() checks.
-- For this challenge, we assume the application layer handles tenant isolation via queries,
-- which is exactly what Bug 1 violates (cache layer ignoring it).
