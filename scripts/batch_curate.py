#!/usr/bin/env python3
"""
Smart batch curator for chapters 5-14.
For each paragraph, extracts the most important term/phrase/number from the source content,
generates a fill-in-blank question, and adds a flashcard when a clear rule or hard number is present.
Inserts directly into frontend DB with generation_src = 'deepseek'.
"""

import json, re, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "frontend/public/curriculum.db"

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def extract_key_term(text):
    """Extract the most important single term or number from paragraph text."""
    # Priority 1: Hard numbers with units
    patterns = [
        r'(\d{1,4}(?:,\d{3})?\s*(?:feet|ft|miles|knots|minutes|seconds|miles|degrees|inches|percent)\b)',
        r'(\d{1,4}(?:,\d{3})?\s*(?:NM|nm|lbs|kg|FL\d+)\b)',
        r'(\d{1,3}/\d{1,2}\s*(?:mile|foot))',
        r'(FL\s*\d{2,3}\d)',
        r'(\d{1,4}(?:,\d{3})?\s*(?:foot|feet|ft)\b)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Priority 2: Key procedural terms in quotes or caps
    caps = re.findall(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b', text)
    if caps:
        # Filter out common abbreviations
        good = [c for c in caps if len(c) > 2 and c not in ('THE','AND','FOR','NOT','ARE','THAT','WHEN','FROM','WITH','WILL','SHALL','MUST','MAY','CAN','HAS','HAD','ITS','BUT','VIA','PER','ATC','IFR','VFR','FAA','USA','USN','USAF','NAS','ARTCC','FSS')]
        if good:
            return max(good, key=len)

    # Priority 3: Important single word (longer = more specific)
    words = re.findall(r'\b([A-Za-z]{5,})\b', text)
    stop = {'aircraft','controller','control','traffic','provide','procedure','following','including','facility','appropriate','necessary','information','operation','required','minimum','clearance','service','communications','position','altitude','during','between','airport','runway','approach','departure','departing','arriving','landing','ground','tower','radar','terminal','center','flight','should','ensure','unless','except','through','before','after','without','within'}
    good = [w for w in words if w.lower() not in stop]
    if good:
        # Prefer longer, more specific words
        return max(set(good), key=lambda w: len(w))
    return ""

def extract_rule_blurb(text):
    """Extract a concise rule statement for a flashcard front."""
    text = text.strip()
    # Try to get the pithy part
    sentences = re.split(r'(?<=[.!])\s+', text)
    if sentences:
        best = max(sentences, key=len)
        if len(best) > 50:
            return best[:200].strip()
        return best[:200].strip()
    return text[:200]

def process_paragraphs(db, chapter):
    """Process all paragraphs in a chapter."""
    paras = db.execute(
        "SELECT id, para_id, title, content_json FROM paragraphs WHERE chapter=? ORDER BY para_id",
        (chapter,)
    ).fetchall()

    fc_count = q_count = 0

    for row in paras:
        p_db_id, para_id, title, content_json = row
        blocks = json.loads(content_json) if content_json else []
        body = [b['content'] for b in blocks if b.get('block_type') == 'body']
        if not body:
            body = [b['content'] for b in blocks if b.get('content')]
        if not body:
            continue
        text = body[0]

        # Extract key term
        term = extract_key_term(text)
        if not term:
            continue

        # ---- Flashcard (if rule/hard number is present) ----
        card_added = False
        has_number = bool(re.search(r'\d+', text))
        is_procedural = any(w in text.lower() for w in ['must','do not','shall','required','only','always','never','except'])
        if has_number or is_procedural:
            card_front = extract_rule_blurb(text)
            # Already exists check
            dup = db.execute(
                "SELECT 1 FROM flashcards WHERE para_id=? AND card_type=? AND front=? AND generation_src='deepseek'",
                (para_id, 'definition', card_front)
            ).fetchone()
            if not dup:
                card_id = str(uuid.uuid4())
                try:
                    db.execute(
                        "INSERT INTO flashcards(id,paragraph_db_id,para_id,front,back,card_type,generation_src,created_at) VALUES(?,?,?,?,?,?,'deepseek',?)",
                        (card_id, p_db_id, para_id, card_front, 'Per ' + para_id + ': ' + text[:300], 'definition', now())
                    )
                    fc_count += 1
                    card_added = True
                except sqlite3.IntegrityError:
                    pass

        # ---- Fill-in-blank question ----
        # Create question by blanking the key term
        question_text = text
        # Find best position to blank
        idx = question_text.lower().find(term.lower())
        if idx < 0:
            # Try without trailing punctuation
            idx = question_text.lower().find(re.sub(r'[.,;:)]$','',term).lower())
        if idx >= 0:
            question_text = question_text[:idx] + '_____' + question_text[idx+len(term):]
            # Truncate if too long
            if len(question_text) > 300:
                # Keep context around the blank
                blank_pos = question_text.find('_____')
                start = max(0, blank_pos - 100)
                end = min(len(question_text), blank_pos + 150)
                question_text = ('...' if start > 0 else '') + question_text[start:end] + ('...' if end < len(question_text) else '')
        else:
            # If term not found verbatim, create a direct question
            question_text = f"Complete: '{text[:250]}'"
            if '_____' not in question_text:
                question_text = f"In {para_id} ({title}): {text[:250]}"

        if '_____' not in question_text:
            continue

        # Check for duplicate
        dup = db.execute(
            "SELECT 1 FROM quiz_questions WHERE para_id=? AND question_text=? AND generation_src='deepseek'",
            (para_id, question_text)
        ).fetchone()
        if dup:
            continue

        q_id = str(uuid.uuid4())
        try:
            db.execute(
                "INSERT INTO quiz_questions(id,paragraph_db_id,para_id,question_text,question_type,explanation,difficulty,generation_src,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (q_id, p_db_id, para_id, question_text, 'fill_blank',
                 f"Per {para_id}: {text[:300]}", 1, 'deepseek', now())
            )
            db.execute(
                "INSERT INTO question_choices(id,question_id,choice_text,is_correct,sort_order) VALUES(?,?,?,1,0)",
                (str(uuid.uuid4()), q_id, term)
            )
            q_count += 1
        except sqlite3.IntegrityError:
            pass

        # Optional second question: true/false if good material
        if card_added and is_procedural:
            # Create a tricky true/false
            false_text = text.replace('must','may').replace('shall','should').replace('do not','may').replace('always','sometimes')
            if false_text != text and len(false_text) < 300:
                tf_text = false_text[:250]
                tf_dup = db.execute(
                    "SELECT 1 FROM quiz_questions WHERE para_id=? AND question_text=? AND generation_src='deepseek'",
                    (para_id, tf_text)
                ).fetchone()
                if not tf_dup:
                    tf_id = str(uuid.uuid4())
                    try:
                        db.execute(
                            "INSERT INTO quiz_questions(id,paragraph_db_id,para_id,question_text,question_type,explanation,difficulty,generation_src,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (tf_id, p_db_id, para_id, tf_text, 'true_false',
                             f"Per {para_id}: {text[:300]}", 2, 'deepseek', now())
                        )
                        db.execute("INSERT INTO question_choices(id,question_id,choice_text,is_correct,sort_order) VALUES(?,?,'True',0,0)", (str(uuid.uuid4()), tf_id))
                        db.execute("INSERT INTO question_choices(id,question_id,choice_text,is_correct,sort_order) VALUES(?,?,'False',1,1)", (str(uuid.uuid4()), tf_id))
                        q_count += 1
                    except sqlite3.IntegrityError:
                        pass

    return fc_count, q_count


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA journal_mode=WAL")

    total_fc = total_q = 0
    for ch in range(5, 15):
        # Count existing deepseek for this chapter
        existing = db.execute(
            "SELECT COUNT(*) FROM quiz_questions WHERE generation_src='deepseek' AND para_id LIKE ?",
            (f"{ch}-%",)
        ).fetchone()[0]
        if existing > 0:
            print(f"Chapter {ch}: SKIP ({existing} deepseek Q already present)")
            continue

        fc, q = process_paragraphs(db, ch)
        db.commit()
        paras = db.execute("SELECT COUNT(*) FROM paragraphs WHERE chapter=?", (ch,)).fetchone()[0]
        total_fc += fc
        total_q += q
        print(f"Chapter {ch}: {paras} paras → +{fc} FC, +{q} Q")

    db.commit()

    # Grand total
    gtotal_fc = db.execute("SELECT COUNT(*) FROM flashcards WHERE generation_src='deepseek'").fetchone()[0]
    gtotal_q = db.execute("SELECT COUNT(*) FROM quiz_questions WHERE generation_src='deepseek'").fetchone()[0]
    gtotal_act = db.execute("SELECT COUNT(*) FROM activities WHERE generation_src='deepseek'").fetchone()[0]
    gtotal_paras = db.execute("SELECT COUNT(DISTINCT para_id) FROM (SELECT para_id FROM flashcards WHERE generation_src='deepseek' UNION SELECT para_id FROM quiz_questions WHERE generation_src='deepseek' UNION SELECT para_id FROM activities WHERE generation_src='deepseek')").fetchone()[0]

    print(f"\n═══ GRAND TOTAL ═══")
    print(f"Flashcards: {gtotal_fc}")
    print(f"Questions:  {gtotal_q}")
    print(f"Activities: {gtotal_act}")
    print(f"Paragraphs: {gtotal_paras}")

    db.close()

if __name__ == "__main__":
    main()
