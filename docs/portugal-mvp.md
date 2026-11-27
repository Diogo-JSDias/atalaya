# Portugal adaptation: initial implementation

This fork is being adapted incrementally. The Spanish sources remain unchanged.

## Implemented

- Diário da República: registered a first-pass scraper for the official RSS index of the 2nd series (all parts, HTML). It filters likely recruitment/research notices by title and preserves the original notice URL. This is intentionally a candidate detector, not a legally complete vacancy classifier; verify each notice and deadline at source.
- Portuguese month names are recognised by `academic_offers.dates.first_date`.
- The classifier recognises a first set of Portuguese academic/research role labels, including professor catedrático, professor associado, professor auxiliar, investigador principal/auxiliar, pós-doutoramento and doutoramento.
- Regression tests cover Portuguese month names and the numeric date format commonly used in Portugal.

## Source research and constraints

### Diário da República

The Diário da República is publicly accessible and provides its first and second series in open electronic formats. Its official help and legal notices describe the public access and reuse framework:

- https://diariodarepublica.pt/dr/geral/ajuda
- https://diariodarepublica.pt/dr/geral/avisos-legais

An official, documented machine-readable endpoint suitable for a daily incremental scraper has not yet been validated in this repository. Do not guess internal website APIs. Next step: identify the published open-data feed/API or RSS index, confirm its terms and response format, then implement a parser that filters second-series recruitment notices and links to the original act.

### Bolsa de Emprego Público (BEP)

An experimental parser exists at `academic_offers/sources/portugal.py`, but it is intentionally **not registered in SOURCES**. Public search indexing confirms that BEP detail pages contain useful fields such as offer code, career, employer and job description. However, automated access to some detail pages returns a permission-denied response. Do not work around access controls. Validate the public listing/feed with BEP or request an official data feed before enabling this source.

## Important implementation rules

- Do not infer a deadline from a publication date. Extract an explicit closing date or an explicit duration and mark calculated dates as estimates.
- Do not apply Spain's regional holiday calendar or Spanish administrative deadline assumptions to Portugal.
- Preserve the original notice URL and the exact wording of the institution and role.
- A failed source must not erase previously collected offers.
- Honour robots.txt, published crawl delays and source terms; use a descriptive User-Agent and a low request frequency.

## Next milestones

1. Validate the RSS parser against several real daily issues; improve notice filtering and extract institutions, deadlines and original notice metadata.
2. Add explicit Portuguese deadline rules only after checking the relevant notice wording and applicable legal rules.
3. Validate BEP automated access or obtain an authorised feed.
4. Add FCT calls and institutional career pages with source-specific tests.
5. Translate/adapt the interface and document Portuguese-specific filters.
