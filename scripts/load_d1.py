#!/usr/bin/env python3
"""verses.jsonl -> SQL партиди за D1 (локално; текстът не влиза в git).
Използване:  python3 scripts/load_d1.py verses.jsonl load/
След това:   for f in load/*.sql; do npx wrangler d1 execute ethbible --remote --file=$f; done
Накрая:      npx wrangler d1 execute ethbible --remote --command "INSERT INTO verses_fts(verses_fts) VALUES('rebuild')"
"""
import json, os, sys

def q(s): return "'" + s.replace("'", "''") + "'"

def main(src, outdir, batch=150):
    os.makedirs(outdir, exist_ok=True)
    rows, n = [], 0
    def flush():
        nonlocal rows, n
        if not rows: return
        sql = "INSERT OR REPLACE INTO verses (id, book, ch, v, text) VALUES\n" + ",\n".join(rows) + ";\n"
        open(f"{outdir}/{n:04d}.sql", "w", encoding="utf-8").write(sql)
        rows, n = [], n + 1
    for line in open(src, encoding="utf-8"):
        d = json.loads(line)
        rows.append(f"({q(d['id'])},{q(d['book'])},{d['ch']},{d['v']},{q(d['text'])})")
        if len(rows) >= batch: flush()
    flush()
    print(f"{n} файла в {outdir}/")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
