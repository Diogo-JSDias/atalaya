# Atalaia: oportunidades académicas e científicas em Portugal

*Atalaia* é um portal de oportunidades académicas e científicas em Portugal, adaptado a partir do projeto aberto [Atalaya](https://github.com/pacocp/atalaya), originalmente criado por [Francisco Carrillo-Pérez](https://pacocp.es).

Todos os dias, a Atalaia recolhe concursos para docentes, vagas de investigação e bolsas a partir de fontes oficiais portuguesas, fundações e universidades, complementados por concursos europeus ERC e MSCA. As oportunidades são classificadas por área e fase de carreira e publicadas num site estático e filtrável. Cada entrada liga ao aviso original.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m academic_offers                 # scrape all sources, update data/, build site/
.venv/bin/python -m academic_offers --build         # rebuild the site from the database only
.venv/bin/python -m academic_offers --only dr,fct  # run selected Portuguese sources only
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

O GitHub Pages num plano gratuito exige um repositório público.

## Fontes portuguesas

| Chave | Fonte | Cobertura |
|---|---|---|
| `dr` | Diário da República, 2.ª Série (RSS) | Avisos de recrutamento, docência e investigação; filtro inicial por título. |
| `fct` | Fundação para a Ciência e a Tecnologia | Concursos abertos, com enriquecimento das páginas oficiais de detalhe. |
| `ulisboa` | Universidade de Lisboa | Recrutamento académico e científico; inclui categoria, vagas, prazo e documento principal. |
| `uporto` | Universidade do Porto | Arquivo de oportunidades abertas; bolsas de investigação e recrutamento académico. |
| `ualg` | Universidade do Algarve | Procedimentos concursais de docentes e investigadores, com datas e documentos oficiais. |
| `uc-apply` | Universidade de Coimbra | UC Apply; bolsas de investigação, docentes e investigadores com candidaturas abertas. |
| `uminho` | Universidade do Minho | Portal central de recrutamento (`recrutamento.uminho.pt`); concursos abertos para docentes de carreira e investigadores (a termo e de carreira), excluindo dirigentes e pessoal técnico/administrativo. |
| `uminho-eeg` | Universidade do Minho – EEG | Apenas concursos abertos para pessoal docente/investigador da Escola de Economia, Gestão e Ciência Política; complementa o portal central (`uminho`). |
| `novafct-investigadores` | NOVA FCT | Concursos para investigadores na página oficial de recrutamento da Faculdade; não inclui concursos docentes ou não docentes. |
| `ubi-docentes` | Universidade da Beira Interior | Concursos para pessoal docente em candidatura aberta. |
| `ubi-investigadores` | Universidade da Beira Interior | Concursos para pessoal investigador; parser separado e sem vagas atuais na secção aberta na data de integração. |
| `nova-ims` | NOVA IMS | Bolsas e recrutamento docente; lê os editais PDF para extrair prazos explícitos ou calcular prazos em dias úteis quando o edital os define. |
| `nova-fcsh` | NOVA FCSH | Concursos para investigadores; usa avisos-extrato oficiais do Diário da República e só apresenta concursos com prazo legal futuro calculável. |
| `ucp-medicina` | Católica – Faculdade de Medicina | Concursos de recrutamento docente; analisa editais PDF e só conserva os que ainda podem estar dentro do prazo, sem inventar a data efetiva de publicação. |
| `ua-investigacao`, `ua-docentes`, `ua-tecnico` | Universidade de Aveiro | Concursos de pessoal investigador e docente, mais o portal JobsUA para pessoal técnico, administrativo e de gestão. |
| `iscte` | Iscte | Portal de concursos docentes, técnicos, investigação e bolsas; inclui a Associação Iscte Conhecimento e Inovação. |
| `ucp-clsbe` | Universidade Católica Portuguesa – Católica-Lisbon | Oportunidades de docência, investigadores doutorados e bolsas publicadas pela CLSBE; não representa todas as escolas da UCP. |
| `ucp-porto` | Universidade Católica Portuguesa – Centro Regional do Porto | Concursos de recrutamento docente e de investigação; analisa a página oficial de oportunidades do Porto. |
| `ucp-fch` | Universidade Católica Portuguesa – Faculdade de Ciências Humanas | Concursos de recrutamento docente e de investigação; analisa a página oficial de oportunidades da FCH. |
| `gimm` | GIMM | Página oficial de oportunidades abertas do instituto. |
| `inl` | INL | Portal Jobvite oficial de posições abertas. |
| `lip` | LIP | Portal oficial de candidaturas; só concursos com estado explicitamente aberto. |
| `inesc-tec` | INESC TEC (Rede LASI) | Portal oficial de oportunidades abertas (bolsas e recrutamento) da unidade associada à Rede LASI. |
| `algoritmi` | Centro ALGORITMI – Universidade do Minho (Rede LASI) | Página oficial de oportunidades abertas (bolsas e posições de investigação) do Centro ALGORITMI, unidade da Rede LASI. |

As vagas da edição de 27/11/2026 incluem novas fontes para Aveiro, Iscte, Católica-Lisbon, GIMM, INL e LIP; a segunda vaga acrescenta os concursos de investigadores da UBI e o portal de recrutamento da NOVA IMS; a terceira acrescenta os concursos da NOVA FCSH e centraliza o cálculo de prazos úteis de Lisboa; a quarta acrescenta a Faculdade de Medicina da Católica, com filtro conservador para editais que a página ainda assinala como decorrentes. A cobertura da UCP inclui a Católica-Lisbon (`ucp-clsbe`), a Faculdade de Medicina em Lisboa (`ucp-medicina`), o Centro Regional do Porto (`ucp-porto`) e a Faculdade de Ciências Humanas (`ucp-fch`), mas continua incompleta nas restantes escolas e campi. A cobertura da Universidade do Minho combina o portal central de recrutamento (`uminho`, para docentes de carreira e investigadores) com o índice próprio da Escola de Economia, Gestão e Ciência Política (`uminho-eeg`). A integração de `uminho`, `inesc-tec` e `algoritmi` assinala a cobertura da Rede LASI através das suas instituições empregadoras participantes, uma vez que a LASI não dispõe de um portal único de contratação. O portal de recrutamento da Fundação Champalimaud é carregado dinamicamente e requer uma integração específica; estas lacunas permanecem assinaladas em aberto, não sendo substituídas por feeds presumidos.

As fontes portuguesas estão numa fase de validação. Confirma sempre os requisitos e prazos no aviso original. A BEP permanece desligada enquanto não existir acesso automatizado autorizado e estável.

## Outras fontes e âmbito

A edição portuguesa ativa apenas as fontes nacionais portuguesas listadas acima e os concursos europeus ERC/MSCA. Os adaptadores de Espanha do projeto original (BOE, AEI, Ikerbasque, ICREA, CSIC, centros e universidades) permanecem no repositório, mas não são executados nem apresentados nesta edição. O filtro da base de dados do site também exclui registos históricos dessas fontes.

Não ativado:
- **BEP:** o parser experimental está desligado enquanto não existir acesso automatizado autorizado e estável.
- **EURAXESS:** ainda não existe um método de recolha oficial, estável e validado; não contornamos bloqueios de pesquisa.
- **Outras universidades e politécnicos:** serão adicionados com parsers e testes próprios.

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

## Issues

Please use Github issues for any problems or requests.

## License

The code is released under the [MIT License](LICENSE). The offers themselves come from public sources;
each listing links to its original notice, and those notices belong to their publishers.
