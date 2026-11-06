"""Explicit offline-source inspection and synthetic-only PostgreSQL import.

This package deliberately provides no real-data apply switch. Approval for that
separate operation must include a reviewed migration tool and cutover runbook.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from logitrack_platform.persistence_validation import SnapshotInvalid, fingerprint, validate_snapshot
from logitrack_platform.postgresql_store import PostgreSQLStore, PersistenceError, configuration


def decode_source(raw):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field requires source reconciliation.')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique_object)


def read_source(path, source_format):
    source = Path(path).resolve(strict=True)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_format == 'json':
        payload = decode_source(source.read_text(encoding='utf-8-sig'))
    elif source_format == 'sqlite':
        # Immutable input must be an offline, checkpointed SQLite export, not a
        # live WAL database. Never open it with the application's SQLite helper.
        if Path(str(source)+'-wal').exists() or Path(str(source)+'-journal').exists():
            raise ValueError('SQLite source must be offline and checkpointed.')
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro&immutable=1', uri=True)) as conn:
            rows = conn.execute("SELECT payload_json FROM app_state WHERE state_key='primary'").fetchall()
            if len(rows) != 1:
                raise ValueError('Canonical SQLite primary state is missing or ambiguous.')
            payload = decode_source(rows[0][0])
    else:
        raise ValueError('Source format must be explicit.')
    if hashlib.sha256(source.read_bytes()).hexdigest() != before:
        raise ValueError('Source changed during inspection.')
    return payload, before


def application_roundtrip(payload):
    # Imports code only: no startup, file hydration, or canonical source read.
    from logitrack_rc_v4_4_api import module
    normalized = module.to_serializable(module.from_serializable(payload))
    # Python equality conflates True with 1 and 1.0 with 1; fingerprints preserve
    # JSON scalar types so the migration cannot silently change those contracts.
    if fingerprint(normalized) != fingerprint(payload):
        raise SnapshotInvalid([{'path': '/', 'code': 'APPLICATION_ROUNDTRIP_WOULD_CONVERT_DATA'}])


def migrate_source(path, source_format, *, apply=False, synthetic=False, reviewed_sha256=None):
    payload, source_hash = read_source(path, source_format)
    graph = validate_snapshot(payload, complete=True)
    application_roundtrip(payload)
    report = {'status': 'DRY_RUN_PASS', 'source_format': source_format,
              'source_sha256': source_hash, 'payload_sha256': fingerprint(payload),
              'counts': graph.counts, 'target_written': False}
    if not apply:
        return report
    settings, environment = configuration()
    if not synthetic or environment != 'test' or not settings['dbname'].startswith('rcatlas_test_'):
        raise ValueError('Apply is restricted to explicitly acknowledged synthetic test databases.')
    if reviewed_sha256 != source_hash:
        raise ValueError('Reviewed source SHA-256 does not match.')
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != source_hash:
        raise ValueError('Source changed after validation.')
    result = PostgreSQLStore().import_snapshot(payload, source_hash)
    actual = PostgreSQLStore().load()
    if actual != payload:
        raise PersistenceError('Imported payload verification failed.')
    return report | result | {'target_written': result['status'] == 'IMPORTED'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--format', choices=['json','sqlite'], required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--reviewed-sha256')
    args = parser.parse_args()
    try:
        print(json.dumps(migrate_source(args.source,args.format,apply=args.apply,
                                       synthetic=args.synthetic,reviewed_sha256=args.reviewed_sha256), indent=2))
    except SnapshotInvalid as exc:
        print(json.dumps({'status':'BLOCKED','issues':exc.issues},indent=2))
        raise SystemExit(1)
    except (ValueError, PersistenceError):
        parser.exit(1, 'Import blocked; source, configuration, or target validation failed.\n')
