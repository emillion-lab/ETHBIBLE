#!/usr/bin/env python3
"""verses.jsonl -> D1 през Cloudflare API. Пуска се от CI (mvr-worker/ethbible-load.yml).
Env: CF_TOKEN, CF_ACC, D1_ID. Логът е публичен: печата само бройки и референции, не текст."""
import json, os, sys, time, urllib.request

ACC, DB, TOKEN = os.environ['CF_ACC'], os.environ['D1_ID'], os.environ['CF_TOKEN']
URL = f'https://api.cloudflare.com/client/v4/accounts/{ACC}/d1/database/{DB}/query'
SCHEMA = [
    "DROP TABLE IF EXISTS verses_fts",
    "DROP TABLE IF EXISTS verses",
    "CREATE TABLE verses (id TEXT PRIMARY KEY, book TEXT NOT NULL, ch INTEGER NOT NULL, v INTEGER NOT NULL, text TEXT NOT NULL)",
    "CREATE INDEX idx_verses_ref ON verses(book, ch, v)",
    "CREATE VIRTUAL TABLE verses_fts USING fts5(text, book UNINDEXED, content='verses', content_rowid='rowid', tokenize='porter unicode61')",
]

def query(sql, params=None):
    body = json.dumps({'sql': sql, 'params': params or []}).encode()
    for attempt in range(4):
        req = urllib.request.Request(URL, body, method='POST', headers={
            'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60))
            if d.get('success'): return d['result'][0]['results']
            err = d.get('errors')
        except Exception as e:
            err = str(e)
        print(f'  опит {attempt+1}: {str(err)[:200]}'); time.sleep(2 ** attempt)
    sys.exit('D1 заявката не мина')

def q(x): return "'" + str(x).replace("'", "''") + "'"

def main(src, max_bytes=90_000):
    """D1: до 100 bound параметъра и до 100 KB на заявка -> литерали, партиди по размер."""
    for s in SCHEMA: query(s)
    rows = [json.loads(l) for l in open(src, encoding='utf-8')]
    head = 'INSERT INTO verses (id, book, ch, v, text) VALUES '
    buf, size, done, calls = [], len(head), 0, 0
    def flush():
        nonlocal buf, size, calls
        if buf: query(head + ','.join(buf)); calls += 1
        buf, size = [], len(head)
        if calls % 50 == 0: print(f'  {done}/{len(rows)}')
    for r in rows:
        lit = f"({q(r['id'])},{q(r['book'])},{int(r['ch'])},{int(r['v'])},{q(r['text'])})"
        n = len(lit.encode()) + 1
        if size + n > max_bytes: flush()
        buf.append(lit); size += n; done += 1
    flush()
    query("INSERT INTO verses_fts(verses_fts) VALUES('rebuild')")
    n = query('SELECT COUNT(*) AS n FROM verses')[0]['n']
    hits = query("SELECT v.book, v.ch, v.v FROM verses_fts f JOIN verses v ON v.rowid = f.rowid "
                 "WHERE verses_fts MATCH 'giants' ORDER BY rank LIMIT 3")
    print(f'заредени: {n}/{len(rows)}')
    print('тест "giants":', [f"{h['book']} {h['ch']}:{h['v']}" for h in hits])
    if n != len(rows): sys.exit('бройката не съвпада')

if __name__ == '__main__':
    main(sys.argv[1])
