-- Geo-Engineering Platform Database Schema
-- Version: 1.0
-- Description: PostgreSQL + PostGIS schema for microservices platform

-- Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- USERS & AUTHENTICATION
-- =============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    user_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Magic Links for passwordless auth
CREATE TABLE magic_links (
    token VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_magic_links_user_id ON magic_links(user_id);
CREATE INDEX idx_magic_links_expires_at ON magic_links(expires_at);
CREATE INDEX idx_magic_links_created_at ON magic_links(created_at);

-- JWT Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jwt_token TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- =============================================================================
-- PROJECTS & JOBS
-- =============================================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    use_case VARCHAR(20) NOT NULL CHECK (use_case IN ('wka', 'road', 'solar', 'terrain')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    crs VARCHAR(20) NOT NULL,  -- e.g., 'EPSG:25832'
    utm_zone INT NOT NULL,      -- Extracted from CRS
    bounds GEOMETRY(Polygon, 4326),  -- WGS84 for display
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_use_case ON projects(use_case);
CREATE INDEX idx_projects_created_at ON projects(created_at);
CREATE INDEX idx_projects_bounds ON projects USING GIST(bounds);

-- Jobs (background processing)
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'fetching_dem', 'calculating', 'computing_costs',
                   'generating_report', 'completed', 'failed')
    ),
    progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,

    -- Input parameters
    input_data JSONB NOT NULL,

    -- Results
    result_data JSONB,
    report_url TEXT,

    -- Constraints
    site_count INT CHECK (site_count <= 123),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_jobs_project_id ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- =============================================================================
-- DEM CACHE
-- =============================================================================

CREATE TABLE dem_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL CHECK (source IN ('hoehendaten', 'upload')),
    utm_zone INT NOT NULL,
    bounds GEOMETRY(Polygon, 4326),  -- WGS84
    bounds_utm GEOMETRY(Polygon, 0),  -- UTM coordinates (no SRID as it varies by zone)

    -- Tile management
    tiles JSONB NOT NULL,  -- [{easting, northing, attribution, cached_at}]
    tiles_count INT NOT NULL DEFAULT 0,

    -- Cache metadata
    attribution TEXT,
    resolution FLOAT,  -- meters
    file_path TEXT,    -- Path to GeoTIFF
    file_size BIGINT,  -- Bytes

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '6 months',
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,

    -- User tracking (NULL for public hoehendaten)
    user_id UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_dem_cache_bounds ON dem_cache USING GIST(bounds);
CREATE INDEX idx_dem_cache_utm_zone ON dem_cache(utm_zone);
CREATE INDEX idx_dem_cache_expires_at ON dem_cache(expires_at);
CREATE INDEX idx_dem_cache_source ON dem_cache(source);

-- DEM Cache tiles (individual 1x1km tiles)
CREATE TABLE dem_tiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utm_zone INT NOT NULL,
    easting INT NOT NULL,   -- Center of 1km tile
    northing INT NOT NULL,  -- Center of 1km tile

    -- Data
    file_path TEXT NOT NULL,
    file_size BIGINT,
    attribution TEXT,

    -- Redis cache key
    redis_key VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '6 months',
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INT DEFAULT 0,

    UNIQUE (utm_zone, easting, northing)
);

CREATE INDEX idx_dem_tiles_zone_coords ON dem_tiles(utm_zone, easting, northing);
CREATE INDEX idx_dem_tiles_expires_at ON dem_tiles(expires_at);

-- =============================================================================
-- RESULTS (Vector outputs)
-- =============================================================================

CREATE TABLE calculation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    site_id INT NOT NULL,  -- Index in input array

    -- Geometry (in project CRS, stored as WGS84)
    point_geometry GEOMETRY(Point, 4326),
    platform_geometry GEOMETRY(Polygon, 4326),
    foundation_geometry GEOMETRY(Polygon, 4326),

    -- Volumes
    foundation_volume FLOAT,  -- m³
    cut_volume FLOAT,         -- m³
    fill_volume FLOAT,        -- m³
    net_volume FLOAT,         -- m³ (cut - fill)

    -- Heights
    ground_elevation FLOAT,   -- m
    platform_height FLOAT,    -- m
    optimization_method VARCHAR(20),

    -- Costs
    total_cost FLOAT,
    cost_breakdown JSONB,

    -- Material balance
    material_balance JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_calc_results_job_id ON calculation_results(job_id);
CREATE INDEX idx_calc_results_point ON calculation_results USING GIST(point_geometry);

-- =============================================================================
-- REPORTS
-- =============================================================================

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    format VARCHAR(10) NOT NULL CHECK (format IN ('html', 'pdf', 'geojson', 'gpkg')),

    -- Storage
    file_path TEXT,
    file_size BIGINT,
    download_url TEXT,

    -- S3 (if enabled)
    s3_key TEXT,

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days',
    download_count INT DEFAULT 0,
    last_downloaded_at TIMESTAMP
);

CREATE INDEX idx_reports_job_id ON reports(job_id);
CREATE INDEX idx_reports_expires_at ON reports(expires_at);

-- =============================================================================
-- REPORT TEMPLATES (Phase 2b)
-- =============================================================================

-- Base Templates (Admin-managed)
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('wka', 'road', 'solar', 'terrain')),
    description TEXT,

    -- Template Content
    html_template TEXT NOT NULL,
    css_template TEXT,

    -- Default Variables
    default_variables JSONB DEFAULT '{}'::jsonb,

    -- Available Sections
    available_sections JSONB DEFAULT '[]'::jsonb,

    -- Permissions
    is_public BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),

    -- Metadata
    version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_report_templates_type ON report_templates(type);
CREATE INDEX idx_report_templates_created_by ON report_templates(created_by);

-- User Template Overrides (User-specific customization)
CREATE TABLE user_template_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES report_templates(id) ON DELETE CASCADE,

    -- Level 1: Branding
    logo_url TEXT,
    company_name VARCHAR(255),
    company_address TEXT,
    company_email VARCHAR(255),
    company_phone VARCHAR(50),
    color_scheme VARCHAR(50) DEFAULT 'standard',

    -- Level 2: Content Control
    enabled_sections JSONB DEFAULT '[]'::jsonb, -- ["overview", "calculations", "costs"]
    custom_text_blocks JSONB DEFAULT '[]'::jsonb, -- [{"position": "after_overview", "title": "...", "text": "..."}]
    custom_fields JSONB DEFAULT '{}'::jsonb, -- {"order_number": "AUF-001", "project_number": "PRJ-042"}

    -- Advanced (Level 3 - optional)
    custom_css TEXT,
    custom_layout JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, template_id)
);

CREATE INDEX idx_user_template_overrides_user_id ON user_template_overrides(user_id);
CREATE INDEX idx_user_template_overrides_template_id ON user_template_overrides(template_id);

-- Template Usage Log (Analytics)
CREATE TABLE report_template_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    template_id UUID NOT NULL REFERENCES report_templates(id),
    report_id UUID REFERENCES reports(id),

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),
    format VARCHAR(10),
    file_size BIGINT
);

CREATE INDEX idx_report_template_usage_user_id ON report_template_usage(user_id);
CREATE INDEX idx_report_template_usage_template_id ON report_template_usage(template_id);
CREATE INDEX idx_report_template_usage_generated_at ON report_template_usage(generated_at);

-- =============================================================================
-- TRIGGERS & FUNCTIONS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-cleanup expired magic links
CREATE OR REPLACE FUNCTION cleanup_expired_magic_links()
RETURNS void AS $$
BEGIN
    DELETE FROM magic_links WHERE expires_at < NOW() AND used = FALSE;
END;
$$ LANGUAGE 'plpgsql';

-- Auto-cleanup expired DEM cache
CREATE OR REPLACE FUNCTION cleanup_expired_dem_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM dem_cache WHERE expires_at < NOW();
    DELETE FROM dem_tiles WHERE expires_at < NOW();
END;
$$ LANGUAGE 'plpgsql';

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Create test user (for development only)
INSERT INTO users (email, created_at) VALUES
    ('test@example.com', NOW()),
    ('demo@geo-engineering.de', NOW());

-- =============================================================================
-- GRANTS (if needed)
-- =============================================================================

-- Grant all privileges to admin user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
