#!/usr/bin/env python3
"""PDF текст -> стихове (JSONL). Използване: parse_verses.py eob.txt out.jsonl
ВАЖНО: out.jsonl е частен индекс. Не се комитва в публично репо."""
import re, sys, json, collections

def toc_titles(t):
    """Заглавията от съдържанието (между 'Table of Contents' и първото тяло)."""
    head = t[:t.index('The First Book of Moses, Genesis', 100)]
    block = head.split('Table of Contents', 1)[1]
    block = block.split('Glossary', 1)[0] + '\nGlossary\n'
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    titles, buf = [], ''
    for l in lines:
        buf = (buf + ' ' + l).strip() if buf else l
        # заглавие, пренесено на 2 реда, свършва с 'of the' / 'or The Book of the'
        if not re.search(r'\b(of the|or|the|and)$', buf):
            titles.append(buf); buf = ''
    return [x for x in titles if x != 'Introduction']

def split_books(t, titles):
    pos, cur = [], t.index('The First Book of Moses, Genesis', 100)
    for ti in titles:
        # заглавието може да е на 2 реда в тялото
        pat = re.escape(ti).replace(r'\ ', r'\s+')
        m = re.compile(r'^' + pat + r'\s*$', re.M).search(t, cur)
        if not m:
            print('НЕ СЕ НАМИРА В ТЯЛОТО:', ti, file=sys.stderr); continue
        pos.append((ti, m.start(), m.end())); cur = m.end()
    out = []
    for i, (ti, s, e) in enumerate(pos):
        end = pos[i+1][1] if i+1 < len(pos) else len(t)
        out.append((ti, t[e:end]))
    return out

VM = re.compile(r'(?:(?<=\s)|^)(\d{1,3})(?:\s+|(?=[“‘"\'(\[⌈<†]))(?=\S)')
def verses(body, start=1):
    """Глава = ред само с число, равно на предходната+1. Стих = вграден ' N ',
    строго последователен. Ред с друго число е част от текста (пренесен номер на стих)."""
    ch, buf, chunks = start - 1, [], []
    for line in body.split('\n'):
        m = re.fullmatch(r'\s*(\d{1,3})\s*', line)
        if m and int(m.group(1)) == ch + 1:
            if ch >= start: chunks.append((ch, ' '.join(buf)))
            ch, buf = ch + 1, []
        elif ch >= start:
            if m: line = m.group(1) + ' '    # номер на стих, останал сам на ред
            buf.append(line.strip())
    if ch >= start: chunks.append((ch, ' '.join(buf)))
    res = []
    for ch, txt in chunks:
        txt = re.sub(r'\s+', ' ', txt).strip()
        marks, nxt = [], 2
        for m in VM.finditer(txt):
            if int(m.group(1)) == nxt:
                marks.append((nxt, m.start(), m.end())); nxt += 1
        starts = [(1, 0, 0)] + marks
        for k, (v, st, e) in enumerate(starts):
            end = starts[k+1][1] if k+1 < len(starts) else len(txt)
            tx = txt[e:end].strip()
            if tx: res.append((ch, v, tx))
    return res

def main(src, dst):
    t = open(src, encoding='utf-8').read().replace('\f', '\n')  # дължината не се мени
    titles = toc_titles(t)
    n = collections.Counter()
    with open(dst, 'w', encoding='utf-8') as f:
        for bi, (title, body) in enumerate(split_books(t, titles)):
            if title == 'Glossary': continue
            # Псалом 151 е номериран като глава 151, не 1
            for ch, v, tx in verses(body, 151 if title == 'Psalm 151' else 1):
                f.write(json.dumps({'id': f'{bi:02d}:{ch}:{v}', 'book': title,
                                    'ch': ch, 'v': v, 'text': tx}, ensure_ascii=False) + '\n')
                n[title] += 1
    tot = sum(n.values())
    print(f'книги: {len(n)}/{len(titles)}  стихове: {tot}')
    for k, c in n.most_common()[-8:]: print(f'  най-малко: {c:5d}  {k}')

if __name__ == '__main__':
    main(*sys.argv[1:3])
