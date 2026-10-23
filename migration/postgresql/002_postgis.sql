CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE rcatlas.geographic_points (
    id text NOT NULL,
    organization_id text NOT NULL REFERENCES rcatlas.organizations(id) DEFERRABLE INITIALLY DEFERRED,
    project_kind text GENERATED ALWAYS AS ('projects'::text) STORED,
    project_id text NOT NULL,
    location geometry(Point,4326) NOT NULL,
    properties jsonb NOT NULL DEFAULT '{}',
    PRIMARY KEY(organization_id,id),
    FOREIGN KEY(project_kind,project_id,organization_id)
        REFERENCES rcatlas.entities(kind,id,organization_id) DEFERRABLE INITIALLY DEFERRED,
    CHECK (NOT ST_IsEmpty(location) AND ST_IsValid(location)),
    CHECK (ST_X(location) BETWEEN -180 AND 180 AND ST_Y(location) BETWEEN -90 AND 90)
);
CREATE INDEX geographic_points_location_gist ON rcatlas.geographic_points USING gist(location);
CREATE INDEX geographic_points_tenant_project ON rcatlas.geographic_points(organization_id,project_id);
ALTER TABLE rcatlas.geographic_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE rcatlas.geographic_points FORCE ROW LEVEL SECURITY;
CREATE POLICY geographic_points_tenant ON rcatlas.geographic_points
    USING (organization_id = current_setting('rcatlas.tenant_id',true))
    WITH CHECK (organization_id = current_setting('rcatlas.tenant_id',true));
