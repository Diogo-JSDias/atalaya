# Source inventory: Spanish academic offers

Checked 2026-11-27 with plain HTTP requests (no browser, no login).

## Verdict per source

| Source | Type | Access | Structure | Verdict |
|---|---|---|---|---|
| **BOE open data API** (`/datosabiertos/api/boe/sumario/YYYYMMDD`) | Permanent university posts (Titular, Catedrático, Permanente Laboral), some research posts | JSON, no key, 200 OK | Section `2B` → department `UNIVERSIDADES` → items with `titulo`, `url_xml`, `url_pdf`. Full text (XML, ~30 KB) contains *Área de conocimiento*, department, plaza code, deadline ("quince días hábiles…") | ✅ **Start here.** ~46 university notices in 10 weekdays (~5/day; one notice can hold several posts). Some are corrections or admin-staff calls, so they need filtering. |
| **EURAXESS** | Research jobs, postdocs, fellowships EU-wide | Search/listing pages with **any query string return 403** to automated clients; the unfiltered search page and **job detail pages return 200** | Detail pages carry schema.org JSON-LD plus Research Field, Country, Deadline, Organisation | ⚠️ Usable only for detail pages. No jobs sitemap. **Ask EURAXESS for a data feed or partnership** rather than working around the block. |
| **EU Funding & Tenders search API** (`api.tech.ec.europa.eu/search-api/prod/rest/search`, POST, public key `SEDIA`) | MSCA, ERC and other EU calls | JSON, 200 OK | `callIdentifier`, `keywords`, `focusArea`, dates | ✅ Good for the **Calls** section (EU programmes). |
| **AEI convocatorias** (Ramón y Cajal, Juan de la Cierva, FPI…) | National calls | Static HTML, 200 | Listing with links to each call | ✅ Scrapeable, low volume (calls change a few times a year). |
| **ICREA**, **Ikerbasque** | Regional calls | Static HTML, 200 | Call pages (e.g. "Research Fellows 2026") | ✅ Easy, low volume. Could even be curated by hand. |
| **CSIC** (`/es/formacion-y-empleo/bolsa-de-empleo`, `/convocatorias`) | Many research/technical contracts | Static HTML, 200 | Listings in HTML | ✅ High value. Needs a dedicated parser. |
| **CNIC** (`/es/empleo/ofertas-empleo`) | Predoc / postdoc / technician | Static HTML, 200, `Crawl-delay: 10` | Clean titles ("Investigador/a Postdoctoral para el grupo de…") | ✅ Easy. Respect the 10 s delay. |
| **ICFO** (`jobs.icfo.eu`) | Research, technician | Static HTML, 200 | Titles in links | ✅ Easy. |
| **CNIO**, **IRB Barcelona**, **CRG** | Research jobs | 200, but little text in the HTML (CRG ~1 KB of text) | Probably loaded by JavaScript or an embedded job board (ATS) | 🟡 Find the underlying ATS feed (often JSON) or use Playwright. |
| **BSC** | Research jobs | 200 but almost empty (7 KB, no keywords) | JS-rendered | 🟡 Playwright or ATS feed. |
| **IMDEA Software** | Research jobs | 403 to scripts | n/a | ❌ Skip, or ask them directly. |
| **Universities' own pages** (UCM, UGR, UB, UAM…) | Contracted staff (Ayudante Doctor, Asociado, Sustituto), research contracts | 200, but every site differs; first-guess URLs were wrong at 6 of 8 universities | Often PDF lists | 🟡 Highest coverage but most work: one curated URL + parser each, ~80 universities. |
| **Regional bulletins** (DOGC, BOJA, BOCM…) | Contracted university staff | Not tested yet | Several have open-data APIs | ⏭️ Phase 2. |

## Takeaways

1. **BOE alone gives a working MVP** for permanent posts: structured, legal to reuse, with area and deadline in the text.
2. **Research centres are mostly easy** static HTML. The hard ones (CRG, CNIO, BSC, IRB) likely use a third-party job board that may expose a cleaner JSON feed.
3. **EURAXESS blocks automated searches.** Don't bypass it: request access, or use it only to enrich offers found elsewhere.
4. **Calls are low-volume and stable**: the EU API, AEI, ICREA and Ikerbasque cover most of them. Each needs a small scraper or a curated list.
5. **University pages are the long tail**: a source registry (YAML with URL, parser type, delay, contact) plus a "source returned 0 offers" alert is essential.
6. **Politeness:** identify the bot with a contact URL in the User-Agent, honour `Crawl-delay`, and fetch at most once a day.

## Proposed phase-1 source list

BOE (universities + CSIC in 2B) · EU Funding & Tenders API · AEI · ICREA · Ikerbasque · CSIC · CNIC · ICFO
