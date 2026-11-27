# Portugal adaptation: initial implementation

This fork is being adapted incrementally. The Spanish sources remain unchanged.

## Implemented

- Diário da República: registered a first-pass scraper for the official RSS index of the 2nd series (all parts, HTML). The parser supports RSS and Atom entries, filters likely recruitment/research notices by title and preserves the original notice URL. Its live response and classification quality still need validation in GitHub Actions; verify each notice and deadline at source.
- FCT: registered a first-pass parser for the official open-concursos tab. It keeps links hosted on fct.pt, deduplicates records and extracts only explicit numeric deadlines. It does not treat the planned or closed tabs as open calls. Live HTML selector coverage and pagination still need validation.
- Portuguese month names are recognised by `academic_offers.dates.first_date`.
- The classifier recognises a first set of Portuguese academic/research role labels, including professor catedrático, professor associado, professor auxiliar, investigador principal/auxiliar, pós-doutoramento and doutoramento.
- Regression tests cover Portuguese month names and the numeric date format commonly used in Portugal.

## Source research and constraints

### Diário da República

The Diário da República is publicly accessible and provides its first and second series in open electronic formats. Its official help and legal notices describe the public access and reuse framework:

- https://diariodarepublica.pt/dr/geral/ajuda
- https://diariodarepublica.pt/dr/geral/avisos-legais

The official RSS subscription page publishes a link for the second series, all parts, in HTML format: https://files.diariodarepublica.pt/rss/serie2-html.xml. The feed URL is grounded in the publisher's own page, although the web preview used during development could not inspect the XML because it does not support the feed content type. The parser is registered, but its response format and results still need to be validated by the repository's runtime. Do not guess internal website APIs.

### Fundação para a Ciência e a Tecnologia (FCT)

The FCT publishes a public [Concursos](https://www.fct.pt/concursos/) index with open, planned and closed calls, plus filters for funding type and scientific domain. Its [Bolsas](https://www.fct.pt/financiamento/programas-de-financiamento/bolsas/) and [Emprego Científico](https://www.fct.pt/financiamento/programas-de-financiamento/emprego-cientifico/) pages describe the main research-opportunity categories. The 2026 calendar is a planning document, not a live vacancy feed. The open listing is now consumed at https://www.fct.pt/concursos/?paged=1&tab=open. The initial parser is deliberately conservative: it preserves same-domain detail links and only accepts a complete numeric date from the listing card as a deadline. The source still needs runtime validation for actual card selectors, pagination and possible detail-page deadlines. Do not scrape myFCT as a substitute: it is a separate application portal and may expose application-management records rather than the public notice index.

### Bolsa de Emprego Público (BEP)

An experimental parser exists at `academic_offers/sources/portugal.py`, but it is intentionally **not registered in SOURCES**. Public search indexing confirms that BEP detail pages contain useful fields such as offer code, career, employer and job description. However, automated access to some detail pages returns a permission-denied response. Do not work around access controls. Validate the public listing/feed with BEP or request an official data feed before enabling this source.

## Important implementation rules

- Do not infer a deadline from a publication date. Extract an explicit closing date or an explicit duration and mark calculated dates as estimates.
- Do not apply Spain's regional holiday calendar or Spanish administrative deadline assumptions to Portugal.
- Preserve the original notice URL and the exact wording of the institution and role.
- A failed source must not erase previously collected offers.
- Honour robots.txt, published crawl delays and source terms; use a descriptive User-Agent and a low request frequency.

## Next milestones

1. Validate the DR RSS and FCT parsers against live responses in GitHub Actions; measure false positives and pagination coverage.
2. Improve extraction of FCT call categories, areas and exact deadlines from each official notice, without inferring missing values.
3. Add explicit Portuguese deadline rules only after checking the relevant notice wording and applicable legal rules.
4. Validate BEP automated access or obtain an authorised feed.
5. Add institutional career pages with source-specific tests, then adapt the interface and Portuguese-specific filters.
