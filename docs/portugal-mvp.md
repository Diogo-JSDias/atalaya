# Portugal adaptation: initial implementation

This fork is being adapted incrementally. The Spanish sources remain unchanged.

## Implemented

- Diário da República: registered a first-pass scraper for the official RSS index of the 2nd series (all parts, HTML). The official subscription page publishes the feed link; the web preview cannot fetch XML content, so live parsing still needs validation in GitHub Actions. The parser filters likely recruitment/research notices by title and preserves the original notice URL. This is a candidate detector, not a legally complete vacancy classifier; verify each notice and deadline at source.
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

The FCT publishes a public [Concursos](https://www.fct.pt/concursos/) index with open, planned and closed calls, plus filters for funding type and scientific domain. Its [Bolsas](https://www.fct.pt/financiamento/programas-de-financiamento/bolsas/) and [Emprego Científico](https://www.fct.pt/financiamento/programas-de-financiamento/emprego-cientifico/) pages describe the main research-opportunity categories. The 2026 calendar is a planning document, not a live vacancy feed. The listing page is the best candidate for a future scraper, but its pagination, filters, HTML structure and terms must be validated before registering an automated source. Preserve each call's detail-page URL and extract deadlines only from the published notice.

### Bolsa de Emprego Público (BEP)

An experimental parser exists at `academic_offers/sources/portugal.py`, but it is intentionally **not registered in SOURCES**. Public search indexing confirms that BEP detail pages contain useful fields such as offer code, career, employer and job description. However, automated access to some detail pages returns a permission-denied response. Do not work around access controls. Validate the public listing/feed with BEP or request an official data feed before enabling this source.

## Important implementation rules

- Do not infer a deadline from a publication date. Extract an explicit closing date or an explicit duration and mark calculated dates as estimates.
- Do not apply Spain's regional holiday calendar or Spanish administrative deadline assumptions to Portugal.
- Preserve the original notice URL and the exact wording of the institution and role.
- A failed source must not erase previously collected offers.
- Honour robots.txt, published crawl delays and source terms; use a descriptive User-Agent and a low request frequency.

## Next milestones

1. Validate the DR RSS parser against several real daily issues; improve notice filtering and extract institutions, deadlines and original notice metadata.
2. Prototype an FCT Concursos index parser after validating pagination and page structure; keep the FCT calendar as discovery/context only.
3. Add explicit Portuguese deadline rules only after checking the relevant notice wording and applicable legal rules.
4. Validate BEP automated access or obtain an authorised feed.
5. Add institutional career pages with source-specific tests, then adapt the interface and Portuguese-specific filters.
