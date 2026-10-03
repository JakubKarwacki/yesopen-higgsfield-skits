"""Transactional scheduling. SQLite is the source of truth; files are artifacts."""
import contextlib
import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")
TERMINAL = {"done", "failed", "cancelled"}
BUSY = {"dispatching", "accepted", "running", "unknown"}


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError("invalid identifier")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def relative(value):
    p = Path(value)
    if not value or str(p)=="." or p.is_absolute() or ".." in p.parts or any(x.startswith(".") for x in p.parts):
        raise ValueError("expected a safe relative artifact path")
    if "private" in p.parts or p.suffix.lower() in {".key", ".pem"}:
        raise ValueError("private reference material cannot be transferred")
    return p


def validate_plan(plan):
    identifier(plan["project_id"])
    identifier(plan["revision"])
    tasks = plan["tasks"]
    if not tasks or len(tasks) > 10000:
        raise ValueError("expected 1..10000 tasks")
    indexed = {}
    for t in tasks:
        key = identifier(t["id"])
        if key in indexed:
            raise ValueError("duplicate task id")
        if t["kind"] not in {"gpu", "talk", "fit", "inspect", "edit", "render", "qa", "encode", "gate"}:
            raise ValueError("unknown stage")
        if t.get("placement", "server") not in {"server", "local"}:
            raise ValueError("invalid placement")
        if t.get("placement") == "local" and (t["kind"] not in {"render", "encode"} or not t.get("reason")):
            raise ValueError("local placement requires render/encode and operational reason")
        indexed[key] = t
    visited, visiting = set(), set()
    def walk(key):
        if key not in indexed:
            raise ValueError("unknown dependency")
        if key in visiting:
            raise ValueError("dependency cycle")
        if key in visited:
            return
        visiting.add(key)
        for dep in indexed[key].get("deps", []):
            walk(dep)
        visiting.remove(key)
        visited.add(key)
    for key in indexed:
        walk(key)


class State:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.tx() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
              INSERT OR IGNORE INTO meta VALUES('accepting','1');
              INSERT OR IGNORE INTO meta VALUES('turn','0');
              CREATE TABLE IF NOT EXISTS active(project TEXT PRIMARY KEY, run TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS runs(
                id TEXT PRIMARY KEY, project TEXT NOT NULL, revision TEXT NOT NULL,
                fingerprint TEXT NOT NULL, cancelled INTEGER NOT NULL DEFAULT 0,
                last_turn INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL,
                UNIQUE(project,revision));
              CREATE TABLE IF NOT EXISTS tasks(
                run TEXT NOT NULL, id TEXT NOT NULL, spec TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'waiting', worker TEXT, prompt TEXT, attempt INTEGER NOT NULL DEFAULT 1,
                result TEXT, error TEXT, started REAL, finished REAL,
                PRIMARY KEY(run,id));
              CREATE TABLE IF NOT EXISTS events(
                seq INTEGER PRIMARY KEY AUTOINCREMENT, run TEXT, task TEXT,
                event TEXT NOT NULL, at REAL NOT NULL);
            """)

    @contextlib.contextmanager
    def tx(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def event(self, db, run, task, event):
        db.execute("INSERT INTO events(run,task,event,at) VALUES(?,?,?,?)", (run, task, event, time.time()))

    def submit(self, plan, prepare, max_pending=2000):
        validate_plan(plan)
        fingerprint = digest(plan)
        with self.tx() as db:
            old = db.execute("SELECT * FROM runs WHERE project=? AND revision=?", (plan['project_id'], plan['revision'])).fetchone()
            if old:
                if old['fingerprint'] != fingerprint:
                    raise ValueError("revision already exists with different inputs; use a new revision")
                return old['id']
            if db.execute("SELECT value FROM meta WHERE key='accepting'").fetchone()[0] != '1':
                raise ValueError("server drained; not accepting work")
            pending = db.execute("SELECT COUNT(*) FROM tasks WHERE state NOT IN ('done','failed','cancelled')").fetchone()[0]
            if pending + len(plan['tasks']) > max_pending:
                raise ValueError("pending task limit reached")
            run = uuid.uuid4().hex
            reused = prepare(run) or {}
            db.execute("INSERT INTO runs(id,project,revision,fingerprint,created) VALUES(?,?,?,?,?)",
                       (run, plan['project_id'], plan['revision'], fingerprint, time.time()))
            db.execute('INSERT OR REPLACE INTO active(project,run) VALUES(?,?)',(plan['project_id'],run))
            for spec in plan['tasks']:
                db.execute("INSERT INTO tasks(run,id,spec) VALUES(?,?,?)", (run, spec['id'], json.dumps(spec)))
            for task_id, result in reused.items():
                db.execute("UPDATE tasks SET state='done',result=?,finished=? WHERE run=? AND id=?",
                           (json.dumps(result),time.time(),run,task_id))
            self.event(db, run, None, "submitted")
            return run

    def history(self, project):
        with self.tx() as db:
            return [r[0] for r in db.execute("SELECT id FROM runs WHERE project=? AND cancelled=0 ORDER BY created DESC", (project,))]

    def snapshot(self, run):
        with self.tx() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (identifier(run),)).fetchone()
            if not row:
                raise ValueError("unknown run")
            result = dict(row)
            active = db.execute('SELECT run FROM active WHERE project=?',(row['project'],)).fetchone()
            result['is_current_revision'] = bool(active and active[0]==run)
            result['tasks'] = [dict(t) for t in db.execute("SELECT * FROM tasks WHERE run=? ORDER BY rowid", (run,))]
            states = [t['state'] for t in result['tasks']]
            result['status'] = ('cancelled' if row['cancelled'] else 'done' if all(s == 'done' for s in states)
                                else 'needs_attention' if any(s in {'failed', 'unknown'} for s in states)
                                else 'in_progress')
            for t in result['tasks']:
                t['spec'] = json.loads(t['spec'])
                t['result'] = json.loads(t['result']) if t['result'] else None
            return result

    def claim(self, worker, accepts, placement='server', only=None):
        with self.tx() as db:
            for run in db.execute("SELECT * FROM runs WHERE cancelled=0 ORDER BY last_turn,created").fetchall():
                rows = db.execute("SELECT * FROM tasks WHERE run=? ORDER BY rowid", (run['id'],)).fetchall()
                states = {t['id']: t['state'] for t in rows}
                for t in rows:
                    spec = json.loads(t['spec'])
                    if only and (run['id'], t['id']) != only:
                        continue
                    if t['state'] != 'waiting' or spec.get('placement', 'server') != placement or not accepts(spec):
                        continue
                    if not all(states[d] == 'done' for d in spec.get('deps', [])):
                        continue
                    turn = int(db.execute("SELECT value FROM meta WHERE key='turn'").fetchone()[0]) + 1
                    db.execute("UPDATE meta SET value=? WHERE key='turn'", (str(turn),))
                    db.execute("UPDATE runs SET last_turn=? WHERE id=?", (turn, run['id']))
                    db.execute("UPDATE tasks SET state='dispatching',worker=?,started=? WHERE run=? AND id=?",
                               (worker, time.time(), run['id'], t['id']))
                    self.event(db, run['id'], t['id'], "dispatching")
                    return {'run': run['id'], 'id': t['id'], 'spec': spec, 'worker': worker, 'attempt': t['attempt']}
        return None

    def update(self, task, state, prompt=None, result=None, error=None):
        with self.tx() as db:
            row = db.execute("SELECT state FROM tasks WHERE run=? AND id=?", (task['run'], task['id'])).fetchone()
            cancelled = db.execute("SELECT cancelled FROM runs WHERE id=?", (task['run'],)).fetchone()[0]
            if cancelled and state in TERMINAL:
                state = 'cancelled'
            db.execute("UPDATE tasks SET state=?,prompt=COALESCE(?,prompt),result=COALESCE(?,result),error=?,finished=? WHERE run=? AND id=? AND attempt=?",
                       (state, prompt, json.dumps(result) if result is not None else None, error,
                        time.time() if state in TERMINAL else None, task['run'], task['id'],task.get('attempt',1)))
            self.event(db, task['run'], task['id'], state)

    def cancel(self, run):
        with self.tx() as db:
            if not db.execute("SELECT id FROM runs WHERE id=?", (identifier(run),)).fetchone():
                raise ValueError("unknown run")
            db.execute("UPDATE runs SET cancelled=1 WHERE id=?", (run,))
            db.execute("UPDATE tasks SET state='cancelled' WHERE run=? AND state='waiting'", (run,))
            self.event(db, run, None, "cancel_requested; running tasks drain without interrupt")

    def approve(self, run, task_id):
        with self.tx() as db:
            t = db.execute("SELECT * FROM tasks WHERE run=? AND id=?", (identifier(run), identifier(task_id))).fetchone()
            if not t or json.loads(t['spec'])['kind'] != 'gate' or t['state'] != 'waiting':
                raise ValueError("not a waiting approval gate")
            if db.execute("SELECT cancelled FROM runs WHERE id=?", (run,)).fetchone()[0]:
                raise ValueError("run cancelled")
            states = dict(db.execute("SELECT id,state FROM tasks WHERE run=?", (run,)))
            if not all(states[d] == 'done' for d in json.loads(t['spec']).get('deps', [])):
                raise ValueError("gate dependencies are not complete")
            db.execute("UPDATE tasks SET state='done',finished=? WHERE run=? AND id=?", (time.time(), run, task_id))
            self.event(db, run, task_id, "approved")

    def retry(self, run, task_id):
        with self.tx() as db:
            t=db.execute("SELECT * FROM tasks WHERE run=? AND id=?",(identifier(run),identifier(task_id))).fetchone()
            if not t or t['state']!='failed':
                raise ValueError('only conclusively failed tasks can be retried; reconcile unknown tasks first')
            if db.execute("SELECT cancelled FROM runs WHERE id=?",(run,)).fetchone()[0]:
                raise ValueError('cancelled run cannot retry')
            db.execute("UPDATE tasks SET state='waiting',attempt=attempt+1,prompt=NULL,worker=NULL,result=NULL,error=NULL,started=NULL,finished=NULL WHERE run=? AND id=?",(run,task_id))
            self.event(db,run,task_id,'explicit_retry')

    def recover(self):
        # Never silently resubmit an operation that may already be running elsewhere.
        with self.tx() as db:
            db.execute("UPDATE tasks SET state='unknown',error='coordinator restarted; reconcile before retry' WHERE state IN ('dispatching','accepted','running')")

    def unresolved(self):
        with self.tx() as db:
            return [dict(t) for t in db.execute("SELECT * FROM tasks WHERE state='unknown'")]

    def drain(self):
        with self.tx() as db:
            db.execute("UPDATE meta SET value='0' WHERE key='accepting'")
            rows = db.execute("SELECT run,id,state,spec FROM tasks WHERE state NOT IN ('done','failed','cancelled')").fetchall()
            reviews, blockers = [], []
            for row in rows:
                task = {'run': row['run'], 'task': row['id'], 'state': row['state']}
                # A waiting approval is durable workflow metadata, not compute work.
                # Never exclude unknown/running states, even for a malformed gate.
                if row['state'] == 'waiting' and json.loads(row['spec'])['kind'] == 'gate':
                    reviews.append(task)
                else:
                    blockers.append(task)
            return {'accepting': False, 'outstanding': len(blockers),
                    'pending_reviews': len(reviews), 'review_tasks': reviews,
                    'blocking_tasks': blockers, 'safe_to_stop': not blockers}

    def resume(self):
        with self.tx() as db:
            db.execute("UPDATE meta SET value='1' WHERE key='accepting'")
        return {'accepting': True}
