-- GraphRAG API Service Database Initialization Script
-- Run this script to set up the initial database schema

-- Create database if not exists (run as superuser)
-- CREATE DATABASE graphrag;

-- Connect to graphrag database
\c graphrag;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schema
CREATE SCHEMA IF NOT EXISTS graphrag;

-- Set search path
SET search_path TO graphrag, public;

-- Create enum types
CREATE TYPE workspace_status AS ENUM ('active', 'inactive', 'archived', 'deleted');
CREATE TYPE job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE query_type AS ENUM ('global', 'local', 'hybrid');

-- Create workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status workspace_status DEFAULT 'active',
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    data_path VARCHAR(500),
    owner_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT unique_workspace_name UNIQUE (name, owner_id)
);

-- Create indexes for workspaces
CREATE INDEX idx_workspaces_status ON workspaces(status);
CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_created ON workspaces(created_at DESC);
CREATE INDEX idx_workspaces_name_trgm ON workspaces USING gin(name gin_trgm_ops);

-- Create indexing_jobs table
CREATE TABLE IF NOT EXISTS indexing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_documents INTEGER DEFAULT 0,
    processed_documents INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Create indexes for indexing_jobs
CREATE INDEX idx_jobs_workspace ON indexing_jobs(workspace_id);
CREATE INDEX idx_jobs_status ON indexing_jobs(status);
CREATE INDEX idx_jobs_created ON indexing_jobs(created_at DESC);

-- Create queries table
CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_type query_type DEFAULT 'global',
    response TEXT,
    parameters JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    user_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for queries
CREATE INDEX idx_queries_workspace ON queries(workspace_id);
CREATE INDEX idx_queries_user ON queries(user_id);
CREATE INDEX idx_queries_created ON queries(created_at DESC);
CREATE INDEX idx_queries_text_trgm ON queries USING gin(query_text gin_trgm_ops);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    content_hash VARCHAR(64),
    file_size BIGINT,
    mime_type VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    indexed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_document_per_workspace UNIQUE (workspace_id, filename)
);

-- Create indexes for documents
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_documents_indexed ON documents(indexed_at);

-- Create users table (if using built-in auth)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    api_key VARCHAR(255) UNIQUE,
    metadata JSONB DEFAULT '{}',
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key) WHERE api_key IS NOT NULL;

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit_logs
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permissions JSONB DEFAULT '[]',
    rate_limit INTEGER DEFAULT 1000,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for api_keys
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- Create functions for updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_indexing_jobs_updated_at BEFORE UPDATE ON indexing_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for workspace statistics
CREATE OR REPLACE VIEW workspace_stats AS
SELECT 
    w.id,
    w.name,
    w.status,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(DISTINCT q.id) as query_count,
    COUNT(DISTINCT j.id) as job_count,
    MAX(q.created_at) as last_query_at,
    MAX(j.created_at) as last_job_at
FROM workspaces w
LEFT JOIN documents d ON w.id = d.workspace_id
LEFT JOIN queries q ON w.id = q.workspace_id
LEFT JOIN indexing_jobs j ON w.id = j.workspace_id
GROUP BY w.id, w.name, w.status;

-- Create materialized view for query performance stats
CREATE MATERIALIZED VIEW IF NOT EXISTS query_performance_stats AS
SELECT 
    workspace_id,
    query_type,
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as query_count,
    AVG(processing_time_ms) as avg_processing_time,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_time_ms) as median_processing_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_processing_time,
    SUM(tokens_used) as total_tokens
FROM queries
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY workspace_id, query_type, DATE_TRUNC('hour', created_at);

-- Create index on materialized view
CREATE INDEX idx_query_perf_stats_workspace ON query_performance_stats(workspace_id);

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA graphrag TO graphrag;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA graphrag TO graphrag;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA graphrag TO graphrag;

-- Insert default admin user (password: admin123 - CHANGE THIS!)
INSERT INTO users (username, email, password_hash, is_admin, is_active)
VALUES (
    'admin',
    'admin@graphrag.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY/Q8DjJGfTjMKC',  -- bcrypt hash of 'admin123'
    true,
    true
) ON CONFLICT (username) DO NOTHING;

-- Create refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_query_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY query_performance_stats;
END;
$$ LANGUAGE plpgsql;

-- Output confirmation
SELECT 'Database initialization completed successfully' as status;