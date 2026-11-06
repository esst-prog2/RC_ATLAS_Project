"""Own and independently verify a NEW loopback-only synthetic PostgreSQL cluster.

Never attach to an existing server. No global environment credentials are copied.
Owned processes and data are retained/stopped, not recursively deleted.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


class DisposablePostgres:
    def __init__(self):
        self.bin = Path(os.environ['RCATLAS_PG_TEST_BIN']).resolve(strict=True)
        parent = Path(os.environ['RCATLAS_PG_TEST_ROOT']).resolve(strict=True)
        self.root = Path(tempfile.mkdtemp(prefix='cluster_',dir=parent)).resolve()
        if not self.root.is_relative_to(parent) or self.root == parent:
            raise RuntimeError('Disposable path verification failed.')
        self.data = self.root/'data'
        self.port = free_port()
        self.password = secrets.token_urlsafe(36)
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('PG','LOGITRACK_'))}
        self.env['PGPASSWORD'] = self.password
        self.started = False

    def _run(self, executable, *args):
        output = self.root/(executable+'.output')
        # A started Windows server inherits pipe handles; use a file so the
        # completed pg_ctl process cannot leave communicate() waiting on them.
        with output.open('w',encoding='utf-8') as log:
            result = subprocess.run([str(self.bin/executable),*map(str,args)], env=self.env,
                                    cwd=self.root, stdout=log, stderr=log, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(f'Disposable PostgreSQL {executable} failed; inspect its disposable log.')
        return output.read_text(encoding='utf-8',errors='replace')

    def start(self):
        if not self.data.exists():
            password_file = self.root/'synthetic-init-secret'
            password_file.write_text(self.password,encoding='utf-8')
            self._run('initdb.exe','-D',self.data,'-U','rcatlas_owner',
                      '--auth=scram-sha-256','--encoding=UTF8','--locale=C','--pwfile',password_file)
            password_file.unlink()  # Only the newly generated disposable credential file.
            with (self.data/'postgresql.conf').open('a',encoding='utf-8') as f:
                f.write(f"\nlisten_addresses='127.0.0.1'\nport={self.port}\nmax_connections=30\n")
        self._run('pg_ctl.exe','-D',self.data,'-l',self.root/'postgres.log','-w','start')
        self.started = True
        # Independent SQL checks verify what actually started, not just the plan.
        with psycopg.connect(self.dsn('postgres',owner=True)) as conn:
            directory,port,addresses = conn.execute(
                "SELECT current_setting('data_directory'),current_setting('port'),"
                "current_setting('listen_addresses')").fetchone()
            if Path(directory).resolve() != self.data or int(port) != self.port or addresses != '127.0.0.1':
                raise RuntimeError('Independent cluster isolation verification failed.')
            system_id = conn.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0]
        (self.root/'isolation.json').write_text(json.dumps({
            'disposable_root':str(self.root),'data_directory':directory,'port':port,
            'listen_addresses':addresses,'system_identifier':str(system_id),
            'source_tree':str(ROOT),'synthetic_only':True,'providers':'disabled',
            'database_credentials':'generated; not retained in evidence',
        },indent=2),encoding='utf-8')

    def stop(self):
        if self.started:
            self._run('pg_ctl.exe','-D',self.data,'-m','fast','-w','stop')
            self.started = False

    def dsn(self, database, *, owner=False):
        return make_conninfo(host='127.0.0.1',port=self.port,dbname=database,
                             user='rcatlas_owner' if owner else 'rcatlas_app',password=self.password,
                             sslmode='disable')

    def create_database(self):
        name = 'rcatlas_test_'+uuid.uuid4().hex[:16]
        with psycopg.connect(self.dsn('postgres',owner=True),autocommit=True) as conn:
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='rcatlas_app'").fetchone():
                conn.execute(sql.SQL('CREATE ROLE rcatlas_app LOGIN PASSWORD {}').format(sql.Literal(self.password)))
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        return name

    def grant_application(self,database):
        with psycopg.connect(self.dsn(database,owner=True)) as conn:
            conn.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            conn.execute('GRANT USAGE ON SCHEMA rcatlas TO rcatlas_app')
            conn.execute('GRANT SELECT ON rcatlas.schema_migrations TO rcatlas_app')
            conn.execute('GRANT SELECT,UPDATE ON rcatlas.workspace TO rcatlas_app')
            for table in ('organizations','entities','relationships','import_receipts','geographic_points'):
                conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON rcatlas.{} TO rcatlas_app')
                             .format(sql.Identifier(table)))

    def app_environment(self,database):
        return {k:v for k,v in os.environ.items() if not k.startswith(('PG','LOGITRACK_'))} | {
            'LOGITRACK_ENVIRONMENT':'test','LOGITRACK_STORAGE_BACKEND':'postgresql',
            'LOGITRACK_DATABASE_URL':self.dsn(database),
            'LOGITRACK_DATA_PATH':str(self.root/'forbidden-fallback.json'),
            'LOGITRACK_SQLITE_PATH':str(self.root/'forbidden-fallback.sqlite3'),
            'LOGITRACK_RELATIONAL_STORE_PATH':str(self.root/'forbidden-warehouse.sqlite3'),
            'LOGITRACK_ENABLE_RELATIONAL_MIRROR':'false','LOGITRACK_ENABLE_REPOSITORY_DOMAINS':'false',
            'LOGITRACK_RUN_SCHEDULER':'false','LOGITRACK_EMAIL_ENABLED':'false',
            'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1',
        }
