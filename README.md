# ATC 7110.65 Learning Platform

A versioned learning platform for FAA Order JO 7110.65 — Air Traffic Control.  
Designed so content can be updated independently of user progress, quiz banks, and curriculum.

## Public Use / Disclaimer

This is an unofficial educational study aid. It is not affiliated with or endorsed by the FAA, and it is not operational guidance, legal guidance, or a substitute for current FAA orders, facility directives, LOAs, training materials, or instructor/supervisor direction.

Generated and curated activities, questions, and flashcards may contain errors or omit context. Learners should use the in-app source links to verify material against current official FAA sources. Aircraft recognition material is derived from FAA JO 7360.1K as supporting reference material, not JO 7110.65 paragraph content.

Aircraft images are treated as candidates until a human verifies aircraft identity, recognition usefulness, and reuse metadata. Do not publish learner-facing image-recognition cards from unreviewed image candidates.

---

## Architecture

```
atc_platform/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI entrypoint
│       ├── api/
│       │   ├── content.py           # Chapter/section/paragraph/search routes
│       │   ├── flashcards.py        # Flashcard CRUD + SRS scheduling
│       │   ├── quizzes.py           # Quiz builder, test bank, attempts
│       │   └── lessons.py           # Lesson sessions + mastery/crowns
│       ├── models/
│       │   ├── schema.sql           # PostgreSQL DDL (core content + quizzes)
│       │   ├── schema_activities.sql
│       │   ├── schema_quiz_addition.sql
│       │   ├── schema_srs_addition.sql
│       │   └── orm.py               # SQLAlchemy models
│       ├── services/
│       │   ├── db.py                # SQLAlchemy session factory
│       │   ├── auth.py              # Minimal auth shim for this snapshot
│       │   ├── srs.py               # Spaced repetition scheduling (SM-2)
│       │   ├── activity_engine.py
│       │   ├── activity_generator.py
│       │   ├── card_generator.py
│       │   ├── question_generator.py
│       │   └── quiz_engine.py
│       └── ingestion/
│           └── pipeline.py          # 7110.65 ZIP → structured JSON parser
├── scripts/
│   ├── db_import.py                 # Loads pipeline JSON → PostgreSQL
│   └── generate_curriculum.py       # Builds portable curriculum.db
└── frontend/
    ├── public/
    │   └── curriculum.db            # Generated SQLite DB served to the browser
    └── src/
        ├── App.jsx                  # Main React shell
        ├── CurriculumMap.jsx
        ├── CurriculumReview.jsx     # Local QA dashboard + review queue
        ├── LessonPlayer.jsx
        └── useCurriculum.js         # sql.js/browser SQLite data layer
```

This extracted snapshot currently includes `content`, `flashcards`, `quizzes`, and `lessons` routes. The original `users`, `scenarios`, and `admin` modules were not part of the files provided.

---

## Tech Stack

| Layer       | Technology          | Why                                           |
|-------------|---------------------|-----------------------------------------------|
| Backend     | Python + FastAPI    | Fast, typed, async-ready, great docs          |
| Database    | PostgreSQL          | Full-text search, UUID support, JSON columns  |
| ORM         | SQLAlchemy 2.x      | Pythonic, migration-friendly                  |
| Frontend    | React + Vite        | Component-based, fast dev cycle               |
| Auth        | JWT (python-jose)   | Stateless, works for both web and future API  |
| Flashcard   | SM-2 algorithm      | Proven spaced-repetition scheduling           |
| Content Gen  | Local deterministic generators | Offline curriculum/activity/question generation |

---

## Database Design Principles

### Versioning
Every content record (`chapters`, `sections`, `paragraphs`, `content_blocks`) is linked to an `order_versions` row.  
When 7110.65BB CHG 2 is imported, **existing records are not modified** — new records are created and the `is_current` flag is updated.

This means:
- User progress, flashcards, and quiz attempts remain valid across version changes
- Instructors can build courses targeting a specific version
- A diff view (`version_changes` table) shows what changed between editions

### Paragraph as the Atomic Unit
The `paragraph` (e.g., `2-1-6`) is the core unit of content.  
Everything — flashcards, quiz questions, scenarios, progress — is linked to a `paragraph.id`.  
When a paragraph changes in a new edition, the `prior_para_id` foreign key links the new version to the old one, preserving history.

### Tagging
Tags are applied in two ways:
1. **Auto-tagged** by the ingestion pipeline (keyword pattern matching)
2. **Human-reviewed** by instructors via the admin portal

Tags drive curriculum filtering: an instructor can build a "TRACON IFR" module by filtering `tag = TRACON AND tag = IFR`.

---

## Quick Start

```bash
# 1. Clone and install Python deps
pip install fastapi sqlalchemy psycopg2-binary python-jose uvicorn

# 2. Create the database
createdb atc_platform
psql atc_platform < backend/app/models/schema.sql
psql atc_platform < backend/app/models/schema_activities.sql
psql atc_platform < backend/app/models/schema_quiz_addition.sql
psql atc_platform < backend/app/models/schema_srs_addition.sql

# 3. Export the DB connection string used by the backend helpers
export DATABASE_URL=postgresql://user:pass@localhost/atc_platform

# 4. Run the ingestion pipeline against your 7110.65 chapter files
python backend/app/ingestion/pipeline.py /path/to/chapter/zips /tmp/parsed.json

# 5. Import into the database
python scripts/db_import.py /tmp/parsed.json \
    --db-url postgresql://user:pass@localhost/atc_platform \
    --edition "7110.65BB" \
    --effective-date 2025-02-20 \
    --set-current

# 6. Start the API
uvicorn backend.app.main:app --reload
# → http://localhost:8000/docs
```

## Build The Browser DB

The React frontend reads a static SQLite file from `frontend/public/curriculum.db`.

```bash
python scripts/generate_curriculum.py \
  --source /path/to/7110.65/files \
  --out curriculum.db \
  --publish frontend/public

python scripts/repair_curriculum.py --db frontend/public/curriculum.db
```

The repair step synchronizes curated content and reapplies the tracked,
chapter-level review decisions in `backend/app/data/content_remediation/`.

If `--chapter` is omitted, the generator now auto-detects any available 7110.65 chapter PDFs/ZIPs in the source directory. It also accepts a single full-order PDF as the source input and will build chapters 1–14 from that file directly.

## Frontend Development

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

Production and GitHub Pages builds use the static browser database committed at
`frontend/public/curriculum.db`:

```bash
cd frontend
VITE_ATC_STATIC_DEPLOY=true npm run build
```

The GitHub Pages workflow builds and publishes `frontend/dist` after changes
are pushed to `main`. Pages must use **GitHub Actions** as its source.

## Trust / Verification Roadmap

- The browser app now includes a local curriculum QA dashboard for paragraph-by-paragraph review of parsed source blocks, generated activities, flashcards, and quiz questions.
- QA review state is local-first and can be exported/imported as JSON, and the review screen supports deep links to the current paragraph/filter state.
- Next, add a learner-facing direct-reference mode that lets users jump from a curriculum paragraph to the corresponding 7110.65 source paragraph/page so they can verify that the platform matches the real order.

---

## Updating for a New 7110.65 Edition or Change

When the FAA publishes a new edition or change order:

1. **Download** the updated chapter files from FAA.gov
2. **Run the pipeline** against the new files:
   ```bash
   python backend/app/ingestion/pipeline.py /path/to/new/files /tmp/new_parsed.json
   ```
3. **Import** with the new edition string:
   ```bash
   python scripts/db_import.py /tmp/new_parsed.json \
       --edition "7110.65BB CHG 2" \
       --effective-date 2026-01-22 \
       --set-current
   ```
4. **Review changed paragraphs** in the admin portal — the `version_changes` table will show what's new/modified/deleted
5. **Update affected quiz questions and flashcards** — the admin portal will flag any learning content linked to modified paragraphs so instructors can review

The platform is designed so Steps 1–3 are fully automated; Steps 4–5 require human review only for changed paragraphs.

---

## API Endpoints (v0.1)

### Content
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/content/versions` | List all imported editions |
| GET | `/api/content/versions/current` | Current active edition |
| GET | `/api/content/chapters` | All chapters (current version) |
| GET | `/api/content/chapters/{id}/sections` | Sections in a chapter |
| GET | `/api/content/paragraphs` | List/filter paragraphs |
| GET | `/api/content/paragraphs/{para_id}` | Single paragraph e.g. `2-1-6` |
| GET | `/api/content/search?q=safety+alert` | Full-text content search |
| GET | `/api/content/tags` | All tags with categories |

### Learning
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/flashcards/due` | Cards due for review (SRS) |
| POST | `/api/flashcards/{id}/review` | Record a flashcard review |
| GET | `/api/quizzes` | Available quizzes |
| POST | `/api/quizzes/{id}/attempt` | Start a quiz attempt |
| POST | `/api/lessons/start` | Start a lesson session |
| POST | `/api/lessons/{id}/answer` | Submit an activity answer |
| GET | `/api/lessons/{id}/summary` | Lesson summary + crown changes |

### Progress
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/lessons/mastery` | User mastery/crown state |
| GET | `/api/lessons/mastery/{para_id}` | Mastery detail for one paragraph |
