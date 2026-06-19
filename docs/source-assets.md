# FAA Source Assets

The platform imports exact FAA JO 7110.65 tables and figures from the official FAA HTML publication rather than redrawing them.

Canonical source:

- HTML: `https://www.faa.gov/air_traffic/publications/atpubs/atc_html/`
- PDF: `https://www.faa.gov/documentLibrary/media/Order/7110.65BB_Bsc_w_Chg_1_and_2_dtd_1-22-26_Final.pdf`

The extraction script is:

```bash
python scripts/extract_faa_source_assets.py --sleep 0
```

It writes:

- `backend/app/data/faa_7110_65bb_source_assets.json`
- `frontend/public/curriculum.db.source_assets`

Run it after any full `curriculum.db` rebuild, then copy the updated DB into `frontend/dist/curriculum.db` after building if previewing the production bundle.

The source drawer renders matched assets for activities that cite `TBL x-y-z` or `FIG x-y-z`. Matching is global by FAA label, so a paragraph can cite a table or figure anchored elsewhere in the same FAA publication.
