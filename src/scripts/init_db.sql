-- RayaShop Agent - Database Initialization
-- This script runs on first `docker compose up`

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    currency VARCHAR(10) DEFAULT 'EGP',
    url TEXT,
    image_url TEXT,
    category VARCHAR(255),
    brand VARCHAR(255),
    attributes JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Scrape jobs tracking
CREATE TABLE IF NOT EXISTS scrape_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(50) DEFAULT 'pending',
    provider VARCHAR(100) NOT NULL,
    target_url TEXT,
    products_found INTEGER DEFAULT 0,
    products_stored INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_products_external_id ON products(external_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING gin(name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status ON scrape_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_created_at ON scrape_jobs(created_at);
