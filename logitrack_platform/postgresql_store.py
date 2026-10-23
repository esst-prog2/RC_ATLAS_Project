"""PostgreSQL canonical persistence. No fallback, implicit import, or runtime DDL."""
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import hashlib
import math
import os

from logitrack_platform.persistence_validation import fingerprint, validate_snapshot


class PersistenceError(RuntimeError):
    pass


class ConfigurationError(PersistenceError):
    pass


class PersistenceUnavailable(PersistenceError):
    pass


class VersionConflict(PersistenceError):
    pass


MIGRATIONS = Path(__file__).resolve().parents[1] / 'migration' / 'postgresql'
MIGRATION_LOCK = 728192601


def migration_files():
    return [(p.name, hashlib.sha256(p.read_bytes()).hexdigest(), p.read_text(encoding='utf-8'))
            for p in sorted(MIGRATIONS.glob('[0-9][0-9][0-9]_*.sql'))]


def configuration():
    try:
        from psycopg.conninfo import conninfo_to_dict
        settings = conninfo_to_dict(os.environ.get('LOGITRACK_DATABASE_URL', ''))
    except Exception:
        raise ConfigurationError('Invalid PostgreSQL configuration.') from None
    if not all(settings.get(k) for k in ('host', 'dbname', 'user', 'password')):
        raise ConfigurationError('PostgreSQL requires explicit host, database, user and secret.')
    if any(k in settings for k in ('service', 'passfile', 'options', 'hostaddr',
                                  'connect_timeout', 'application_name')):
        raise ConfigurationError('Unsupported PostgreSQL connection override.')
    environment = os.environ.get('LOGITRACK_ENVIRONMENT', 'production').lower()
    if environment not in {'production', 'development', 'test'}:
        raise ConfigurationError('Unknown persistence environment.')
    if environment in {'development', 'test'}:
        if settings['host'] not in {'127.0.0.1', 'localhost', '::1'}:
            raise ConfigurationError('Disposable development databases must use loopback.')
    else:
        if settings.get('sslmode') != 'verify-full' or not settings.get('sslrootcert'):
            raise ConfigurationError('Production PostgreSQL requires verified TLS.')
        if settings['user'].lower() in {'postgres', 'rcatlas_test', 'rcatlas_dev'} or (
            settings['password'].lower() in {'postgres', 'password', 'test', 'development'}
            or len(settings['password']) < 24
        ):
            raise ConfigurationError('Production database credentials are not acceptable.')
        if os.environ.get('LOGITRACK_SESSION_COOKIE_SECURE', '').lower() in {'false','0','no','off'}:
            raise ConfigurationError('Production requires secure session cookies.')
    return settings, environment


@contextmanager
def connection(*, migrator=False):
    settings, environment = configuration()
    try:
        import psycopg
    except ImportError:
        raise ConfigurationError('The PostgreSQL driver is not installed.') from None
    conn = None
    try:
        with psycopg.connect(**settings, connect_timeout=5,
                             application_name='rcatlas_migration' if migrator else 'rcatlas',
                             options='-c search_path=rcatlas,public -c statement_timeout=15000 '
                                     '-c lock_timeout=5000 -c idle_in_transaction_session_timeout=20000') as conn:
            if not 170000 <= conn.info.server_version < 180000:
                raise ConfigurationError('This adapter requires PostgreSQL major version 17.')
            if not migrator:
                privileged = conn.execute(
                    'SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls '
                    'FROM pg_roles WHERE rolname=current_user').fetchone()[0]
                if privileged:
                    raise ConfigurationError('Application database role must be unprivileged.')
                if environment == 'production' and conn.execute(
                    "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='rcatlas' "
                    'AND nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user))'
                ).fetchone()[0]:
                    raise ConfigurationError('Application role must not own the schema.')
            yield conn
    except psycopg.Error:
        # Neither DSNs nor raw SQL/server diagnostics cross the public boundary.
        raise PersistenceUnavailable('PostgreSQL operation failed; no fallback was attempted.') from None
    finally:
        if conn is not None:
            conn.close()


def check_schema(conn):
    if conn.execute("SELECT to_regclass('rcatlas.schema_migrations')").fetchone()[0] is None:
        raise ConfigurationError('PostgreSQL schema migrations are incomplete.')
    applied = conn.execute('SELECT name,sha256 FROM rcatlas.schema_migrations ORDER BY name').fetchall()
    expected = [(name, sha) for name, sha, _ in migration_files()]
    if applied != expected:
        raise ConfigurationError('PostgreSQL schema version or checksum does not match.')
    row = conn.execute("SELECT extversion FROM pg_extension WHERE extname='postgis'").fetchone()
    if row is None or not row[0].startswith('3.6.'):
        raise ConfigurationError('PostGIS 3.6 is required.')


def migrate_schema():
    """Explicit operator operation. Each complete upgrade is transactional."""
    with connection(migrator=True) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(%s)', (MIGRATION_LOCK,))
        conn.execute('CREATE SCHEMA IF NOT EXISTS rcatlas')
        conn.execute('CREATE TABLE IF NOT EXISTS rcatlas.schema_migrations '
                     '(name text PRIMARY KEY, sha256 text NOT NULL, '
                     'applied_at timestamptz NOT NULL DEFAULT clock_timestamp())')
        applied = conn.execute('SELECT name,sha256 FROM rcatlas.schema_migrations ORDER BY name').fetchall()
        files = migration_files()
        if applied != [(name, sha) for name, sha, _ in files[:len(applied)]]:
            raise ConfigurationError('Migration history is unknown or modified.')
        completed = []
        for name, sha, statement in files[len(applied):]:
            conn.execute(statement)
            conn.execute('INSERT INTO rcatlas.schema_migrations(name,sha256) VALUES (%s,%s)', (name, sha))
            completed.append(name)
        check_schema(conn)
        return completed


def _write_graph(conn, graph):
    from psycopg.types.json import Jsonb
    # Deferrable FKs allow atomic replacement while preserving existing spatial FKs.
    conn.execute('DELETE FROM rcatlas.relationships')
    conn.execute('DELETE FROM rcatlas.entities')
    conn.execute('DELETE FROM rcatlas.organizations')
    timestamp = conn.execute('SELECT transaction_timestamp()').fetchone()[0]
    def active_receipt(kind, attributes):
        return kind == 'idempotency_records' and datetime.fromisoformat(
            attributes['expires_at'].replace('Z','+00:00')) > timestamp
    with conn.cursor() as cur:
        cur.executemany('INSERT INTO rcatlas.organizations(id) VALUES (%s)', [(x,) for x in graph.organizations])
        cur.executemany('INSERT INTO rcatlas.entities(kind,id,organization_id,project_id,attributes,idempotency_active) '
                        'VALUES (%s,%s,%s,%s,%s,%s)',
                        [(k, i, o, p, Jsonb(a), active_receipt(k,a)) for k, i, o, p, a in graph.entities])
        cur.executemany('INSERT INTO rcatlas.relationships '
                        '(source_kind,source_id,organization_id,field,target_kind,target_id) '
                        'VALUES (%s,%s,%s,%s,%s,%s)', graph.relationships)


class PostgreSQLStore:
    def load(self):
        with connection() as conn:
            check_schema(conn)
            row = conn.execute('SELECT payload FROM rcatlas.workspace WHERE singleton').fetchone()
            if row is None:
                raise ConfigurationError('Canonical PostgreSQL workspace is missing.')
            return row[0]

    def save(self, payload, expected_version):
        from psycopg.types.json import Jsonb
        graph = validate_snapshot(payload, complete=True)
        with connection() as conn:
            check_schema(conn)
            row = conn.execute('SELECT version FROM rcatlas.workspace WHERE singleton FOR UPDATE').fetchone()
            if row is None:
                raise ConfigurationError('Canonical PostgreSQL workspace is missing.')
            if row[0] != expected_version:
                raise VersionConflict('The workspace changed. Reload and retry.')
            version = expected_version + 1
            saved = dict(payload, workspace_version=version)
            _write_graph(conn, graph)
            conn.execute('UPDATE rcatlas.workspace SET payload=%s,version=%s,updated_at=clock_timestamp() '
                         'WHERE singleton', (Jsonb(saved), version))
        return version

    def status(self):
        with connection() as conn:
            check_schema(conn)
            row = conn.execute('SELECT version FROM rcatlas.workspace WHERE singleton').fetchone()
            return {'backend': 'postgresql', 'exists': row is not None,
                    'workspace_version': row[0] if row else None,
                    'server_version': conn.info.server_version,
                    'postgis_version': conn.execute('SELECT postgis_lib_version()').fetchone()[0]}

    def import_snapshot(self, payload, source_sha256):
        """Atomic empty-target import; caller must enforce the synthetic execution gate."""
        from psycopg.types.json import Jsonb
        graph = validate_snapshot(payload, complete=True)
        digest = fingerprint(payload)
        with connection() as conn:
            check_schema(conn)
            current_version, current = conn.execute(
                'SELECT version,payload FROM rcatlas.workspace WHERE singleton FOR UPDATE').fetchone()
            receipt = conn.execute('SELECT payload_sha256 FROM rcatlas.import_receipts WHERE source_sha256=%s',
                                   (source_sha256,)).fetchone()
            if receipt:
                if receipt[0] != digest or fingerprint(current) != digest:
                    raise VersionConflict('Previously imported workspace has changed.')
                return {'status': 'UNCHANGED', 'counts': graph.counts, 'sha256': digest}
            if current != {'workspace_version': 0} or current_version != 0:
                raise VersionConflict('Import requires an empty initialized target.')
            _write_graph(conn, graph)
            conn.execute('UPDATE rcatlas.workspace SET payload=%s,version=%s,updated_at=clock_timestamp() '
                         'WHERE singleton', (Jsonb(payload), payload['workspace_version']))
            conn.execute('INSERT INTO rcatlas.import_receipts '
                         '(source_sha256,payload_sha256,imported_version,counts) VALUES (%s,%s,%s,%s)',
                         (source_sha256,digest,payload['workspace_version'],Jsonb(graph.counts)))
            actual = dict(conn.execute('SELECT kind,count(*) FROM rcatlas.entities GROUP BY kind').fetchall())
            actual['relationships'] = conn.execute('SELECT count(*) FROM rcatlas.relationships').fetchone()[0]
            if actual != graph.counts:
                raise PersistenceError('Imported row counts do not match.')
        return {'status': 'IMPORTED', 'counts': graph.counts, 'sha256': digest}

    def save_point(self, *, organization_id, project_id, point_id, longitude, latitude):
        if not organization_id or not project_id or not point_id:
            raise ValueError('Spatial ownership and identifiers are required.')
        if not all(isinstance(x, (int,float)) and math.isfinite(x) for x in (longitude,latitude)) or (
            not -180 <= longitude <= 180 or not -90 <= latitude <= 90
        ):
            raise ValueError('WGS84 coordinates are outside their valid range.')
        with connection() as conn:
            check_schema(conn)
            # Serialize with aggregate writes, including project removal.
            conn.execute('SELECT version FROM rcatlas.workspace WHERE singleton FOR UPDATE')
            conn.execute("SELECT set_config('rcatlas.tenant_id',%s,true)", (organization_id,))
            conn.execute('INSERT INTO rcatlas.geographic_points(id,organization_id,project_id,location) '
                         'VALUES (%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326)) '
                         'ON CONFLICT(organization_id,id) DO UPDATE SET project_id=excluded.project_id, '
                         'location=excluded.location', (point_id,organization_id,project_id,longitude,latitude))

    def list_points(self, organization_id):
        if not organization_id:
            raise ValueError('Spatial tenant context is required.')
        with connection() as conn:
            check_schema(conn)
            conn.execute("SELECT set_config('rcatlas.tenant_id',%s,true)", (organization_id,))
            return conn.execute('SELECT id,project_id,ST_X(location),ST_Y(location),ST_SRID(location) '
                                'FROM rcatlas.geographic_points WHERE organization_id=%s ORDER BY id',
                                (organization_id,)).fetchall()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Explicit PostgreSQL schema migration (no data import).')
    parser.add_argument('command', choices=['migrate', 'check'])
    command = parser.parse_args().command
    try:
        print({'applied': migrate_schema()} if command == 'migrate' else PostgreSQLStore().status())
    except PersistenceError as exc:
        parser.exit(1, str(exc)+'\n')
