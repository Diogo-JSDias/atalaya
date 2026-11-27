# Portuguese university and research-centre target landscape

**Snapshot:** 27 November 2026  
**Purpose:** prioritise recruitment-source coverage for the Portuguese Atalaia edition.

## Method

- **Universities:** national order based on the QS World University Rankings 2027, using the published global positions for Portuguese institutions. This is a practical overall ranking, not a subject-specific assessment. Ranking providers and editions can disagree; refresh this list annually.
- **Research organisations:** the five highest-ranked non-university Portuguese research organisations visible in the latest Nature Index Portugal institution-output table available for this review (time frame 1 July 2025–30 June 2026). Nature Index measures output in its selected natural-science journals; it is not a comprehensive measure of research quality across all disciplines and is not the FCT unit-evaluation ranking.
- **Matching:** “direct” means Atalaia has an active source for that university. “partial” means an active source covers only a faculty, portal, or recruitment category. Research-centre links are marked as formal/founding relationship, partnership, or documented collaboration; collaboration does not imply ownership.

## Top 10 universities

| PT tier | University | QS 2027 global position | Atalaia source today | Coverage assessment |
|---:|---|---:|---|---|
| 1 | Universidade de Lisboa (ULisboa) | 237 | `ulisboa` | Partial: central academic/scientific index; school and institute sites still need individual coverage |
| 2 | Universidade do Porto (U.Porto) | 255 | `uporto` | Partial: central opportunity archive; not every faculty or associated institute |
| 3 | Universidade NOVA de Lisboa | 337 | `novafct-investigadores`, `nova-ims` | Partial: NOVA FCT researcher calls and NOVA IMS recruitment; other schools and Reitoria channels remain |
| 4 | Universidade de Coimbra | 342 | `uc-apply` | Partial: central UC Apply index covers scholarships, researchers and teaching; not every faculty/technical channel |
| 5 | Universidade de Aveiro | 425 | `ua-investigacao`, `ua-docentes`, `ua-tecnico` | Partial: central researcher, teaching and technical/administrative channels; associated units remain |
| 6 | Universidade do Minho | 572 | `uminho-eeg` | Partial: EEG only; central portal currently has no open academic/research calls and its detail flow needs validation |
| 7 | Universidade Católica Portuguesa | 791–800 | `ucp-clsbe` | Partial: Católica-Lisbon research/teaching/doctoral scholarship page only; Porto, Braga and other schools remain |
| 8 | ISCTE – Instituto Universitário de Lisboa | 851–900 | `iscte` | Partial: central recruitment portal and Iscte Knowledge & Innovation association; school/unit coverage remains |
| 9 | Universidade da Beira Interior (UBI) | 901–950 | `ubi-docentes`, `ubi-investigadores` | Partial: separate teaching and researcher recruitment sections; researcher section had no open rows at review |
| 10 | Universidade do Algarve (UAlg) | 1001–1200 | `ualg` | Partial/direct source: docente and researcher competitions |

**Coverage summary:** 10/10 universities now have at least one active source. None should be interpreted as fully covered: several schools, associated institutes, technical channels and local recruitment pages still require dedicated validation.

## Top 5 Portuguese research organisations to monitor

Ordered by the latest available Nature Index Portugal institution-output position among non-university organisations. These are research organisations/laboratories, not five identically structured university departments.

| Nature Index PT position | Organisation | Main areas | University matches and relationship | Atalaia relevance |
|---:|---|---|---|---|
| 7 | Gulbenkian Institute for Molecular Medicine (GIMM) | Molecular medicine, life and health sciences | **ULisboa:** founding institution through the Faculty of Medicine and University of Lisbon. **NOVA:** documented domestic research collaboration, not a founding relationship. | High: monitor GIMM careers/recruitment and distinguish institute vacancies from ULisboa/NOVA vacancies. |
| 8 | Champalimaud Foundation | Neuroscience, cancer, clinical and translational research | **NOVA:** formal strategic research and training partnership signed in July 2026. | High: independent employer with a strong university partnership; individual vacancies are visible but the central listing is dynamically loaded, so a stable index is still needed. |
| 9 | International Iberian Nanotechnology Laboratory (INL) | Nanoscience, nanotechnology, materials, energy and health | **U.Porto and UMinho:** documented domestic research collaborations in Nature Index. | High: independent international laboratory; monitor its own careers page, not just university portals. |
| 10 | Laboratory of Instrumentation and Experimental Particle Physics (LIP) | Particle physics, astroparticle physics and instrumentation | **ULisboa, U.Porto, UC and UMinho:** universities are listed as LIP associates; also linked through the IDPASC network. | High: multi-university research employer; one LIP feed could complement several university feeds. |
| 13 | Intelligent Systems Associate Laboratory (LASI) | AI, intelligent systems, robotics and digital technologies | **UMinho:** associated laboratory based at UMinho. **U.Porto, Aveiro and ULisboa:** documented domestic collaborations; includes research groups across institutions. | High: cross-university laboratory; source should identify the employing host institution for each vacancy. |

## Matching against current Atalaia coverage

| Research organisation | Matched universities in top 10 | Existing Atalaia university coverage | Recommended treatment |
|---|---|---|---|
| GIMM | ULisboa; NOVA | ULisboa active; NOVA FCT and NOVA IMS partial | GIMM has its own independent Atalaia feed; do not infer employer from university collaboration |
| Champalimaud Foundation | NOVA | NOVA FCT and NOVA IMS partial | Keep as an independent target; the dynamic careers list still needs a stable data feed |
| INL | U.Porto; UMinho | U.Porto active; UMinho EEG-only partial | INL has its own independent Atalaia feed |
| LIP | ULisboa; U.Porto; Coimbra; UMinho | All four have partial sources | LIP has its own independent Atalaia feed; preserve LIP as employer and host institution separately |
| LASI | UMinho; U.Porto; Aveiro; ULisboa | All four universities now have at least one partial Atalaia source | No single LASI employer portal was identified; add member-unit feeds and preserve the actual hiring institution |

## Recommended acquisition order

1. **Champalimaud Foundation** — find a stable index/API for the dynamically loaded careers list.
2. **NOVA** — expand beyond NOVA FCT and NOVA IMS into Reitoria, FCSH, Medical School, ITQB, IHMT, Law, SBE and other schools; reject stale lists.
3. **Católica Portuguesa** — extend beyond Católica-Lisbon into Porto, Braga and other regional schools where staff calls are published.
4. **UMinho, ULisboa and U.Porto** — expand beyond existing central/school-level coverage with verified faculty and institute feeds.
5. **LASI** — add sources from participating member units and preserve the employer/host attribution.

For each new adapter, use the official careers/recruitment page, retain the original notice URL and deadline, exclude expired/closed calls, fail visibly if the listing structure changes, and add offline parser tests before activation. Avoid inferring the employer from a university collaboration alone.

## Sources

### University ranking
- QS World University Rankings: Southern Europe 2026 / Portugal filter: https://www.topuniversities.com/europe-university-rankings-southern-europe?countries=pt
- Study.eu Portugal ranking table (QS 2027 positions): https://www.study.eu/best-universities/portugal
- University of Porto's 22 June 2026 summary of the QS 2026 Portuguese order: https://noticias.up.pt/en/2026/06/22/u-porto-strengthens-its-position-among-the-worlds-top-universities-in-the-qs-ranking/

### Research output and affiliations
- Nature Index Portugal institution outputs (latest period shown): https://www.nature.com/nature-index/institution-outputs/generate/all/countries-Portugal/all
- GIMM founding institutions and history: https://gulbenkian.pt/en/a-new-scientific-era/
- Nature Index GIMM collaborations: https://www.nature.com/nature-index/institution-outputs/Portugal/Gulbenkian%20Institute%20for%20Molecular%20Medicine%20%28GIMM%29/513906c034d6b65e6a0006e2
- NOVA–Champalimaud strategic partnership, 29 July 2026: https://www.unl.pt/en/noticias/nova/nova-signs-partnership-with-the-champalimaud-foundation-to-accelerate-health-research/
- Nature Index INL collaborations: https://www.nature.com/nature-index/institution-outputs/Portugal/International%20Iberian%20Nanotechnology%20Laboratory%20%28INL%29/62053dbab70e3904724e8ccc
- LIP associates and institutional network: https://www.lip.pt/lfiles/Relatorio-Publico.pdf and https://idpasc.lip.pt/portugal
- LASI profile and domestic collaborations: https://www.nature.com/nature-index/institution-outputs/Portugal/Intelligent%20Systems%20Associate%20LAboratory%20%28LASI%29/67452b7a949a6dc554009baa
- LASI description at U.Porto: https://www.up.pt/feup/en/associated-laboratories/associated-laboratories/intelligent-systems-associate-laboratory/

### Atalaia coverage checked
- Active source registry: `academic_offers/sources/__init__.py`
- Current source scope: `README.md`
- Current wave status: Aveiro, Iscte, Católica-Lisbon, GIMM, INL and LIP feeds are integrated; UBI researcher and NOVA IMS sources were added in the November 2026 expansion wave.
