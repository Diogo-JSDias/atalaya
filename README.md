# Atalaya: plazas académicas en España

*Atalaya* (Spanish for "watchtower"): one lookout over academic posts and research funding across Spain.

Every day Atalaya collects open faculty posts, research jobs and funding calls from official bulletins,
funders, research centres and universities, classifies them by field and career stage, and publishes a
static, filterable website. Each listing links back to its original notice.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m academic_offers                 # scrape all sources, update data/, build site/
.venv/bin/python -m academic_offers --build         # rebuild site/ from the database only
.venv/bin/python -m academic_offers --only boe,crg  # run some sources only
.venv/bin/python -m unittest discover -s tests      # offline tests
python3 -m http.server 8766 --directory site        # preview at http://localhost:8766
```

## Publishing (GitHub Pages)

`.github/workflows/daily.yml` runs every day at 07:30 UTC, on demand ("Run workflow"), and on code changes:
tests → scrape → commit `data/` → deploy `site/` to GitHub Pages.

One-time setup on GitHub:
1. Create a repository and push this folder to it.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
3. *(Optional)* **Settings → Secrets and variables → Actions → New secret** `ANTHROPIC_API_KEY`, to turn on AI
   extraction of PDF annexes. Optional variables: `ATALAYA_LLM_MAX_CALLS` (default 40 per run),
   `ATALAYA_LLM_MODEL` (default `claude-haiku-5-5`).
4. **Actions → Daily update → Run workflow** for the first deploy.

GitHub Pages on a free account needs a public repository.

## Sources

| Key | Source | Notes |
|---|---|---|
| `boe` | BOE open-data API, section II.B | University faculty posts and CSIC research posts. One entry per *área de conocimiento*; deadline estimated from "N días hábiles/naturales" with national + regional holidays. Notices whose posts can't be parsed go to the AI step, or stay as one "see notice" entry. |
| `eu-ft` | EU Funding & Tenders API | MSCA and ERC calls |
| `aei` | Agencia Estatal de Investigación | Open national calls (RYC, JdC, FPU…), deadline from the call page |
| `ikerbasque`, `icrea` | Regional funders | Closed calls dropped; ICREA shown as "upcoming" between calls |
| `cnic`, `icfo`, `crg`, `cnio`, `irb` | Research centres' job boards | Deadlines read from each job page |
| `uni:*` | University pages (UCM, UGR, UC3M) | Contracted faculty: Ayudante Doctor, Permanente Laboral, Asociado. Add more in `sources/universities.py` → `PAGES` |

Not covered, and why:
- **BSC:** its site is behind an anti-bot challenge, which Atalaya doesn't try to get past.
- **CSIC's own job board:** rendered client-side. CSIC posts published in the BOE are included.
- **EURAXESS:** blocks automated search. A data-feed request is drafted in `docs/euraxess-data-request.md`.
- **Regional bulletins (BOJA, DOGC, BOCM…):** not yet; universities' own pages cover the same contract calls more directly.

## How it works

| Path | Role |
|---|---|
| `academic_offers/sources/` | One module per kind of source; `__init__.py` is the registry |
| `academic_offers/llm.py` | Optional AI extraction (Claude), cached in `data/llm_cache.json`, capped per run |
| `academic_offers/classify.py` | Keyword rules → field / subfield and career stage |
| `academic_offers/store.py` | SQLite history; an offer is shown while its source's latest successful run lists it and its deadline hasn't passed |
| `academic_offers/http.py` | Polite client: `AtalayaBot` user agent, robots.txt + Crawl-delay, ≥2 s per host, 6 h cache |
| `templates/` | Main page and About page (with per-source status) |

A source that crashes keeps its previous offers online and raises a warning in the Actions run.
A source that normally has items but suddenly returns none also raises a warning.
