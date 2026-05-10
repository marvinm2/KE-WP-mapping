# Demo script — Molecular AOP Builder

A one-page operational checklist for live demos at
https://molaop-builder.vhp4safety.nl. Glance at this on a phone or
second screen while presenting; don't read it aloud.

## Pre-demo checklist (5 minutes before going live)

```
[ ] Open these tabs in order, in one browser window:
    1. https://molaop-builder.vhp4safety.nl/                 (mapper home)
    2. https://molaop-builder.vhp4safety.nl/explore           (browse)
    3. https://molaop-builder.vhp4safety.nl/admin/proposals   (admin)
    4. https://molaop-builder.vhp4safety.nl/api/docs          (Swagger)
    5. https://molaop-builder.vhp4safety.nl/downloads         (exports)
    6. https://molaop-builder.vhp4safety.nl/documentation     (in-app docs)

[ ] Log in via your usual provider on tab 1 — confirm the "Admin"
    badge appears next to your username (you'll need it for the
    approval step).

[ ] On tab 1, dismiss the magenta v1.5 banner once (X button).
    It uses localStorage so it stays dismissed for the session.

[ ] If you do NOT plan to demo Reactome: open the Reactome tab on
    /explore once and dismiss the blue "under development" notice.

[ ] On tab 1, type "KE 149" in the KE selector — confirm the AOP
    context graph fans out and suggestion cards render.
    Backup KE: "KE 1825" (12 AOPs, more dramatic graph).

[ ] curl https://molaop-builder.vhp4safety.nl/health
    Expect: "status":"healthy" and "version":"2.7.0".

[ ] Browser zoom: 110–125%. Close DevTools. Mute notifications.

[ ] Have a Plan B folder of screenshots open in Finder/Files in case
    the network drops mid-talk.
```

## Demo storyboard (~5 minutes, ~8 beats)

| # | Tab / URL | Click / Say | What the audience sees |
|---|-----------|-------------|------------------------|
| 1 | mapper `/` | Type "KE 149" — *"Inflammation as a key event sits in 9 different AOPs."* | Cytoscape AOP-context graph fans out — sells "one KE, many AOPs" |
| 2 | mapper | Scroll to WP suggestions; hover the top card. *"Ranked by BioBERT semantic similarity. Gene overlap is shown as a chip but doesn't bias ordering — that's the v1.5 change we shipped this week."* | Cards with score badge + `Genes: N/M` chip |
| 3 | mapper | Click a suggested pathway → embedded WikiPathways viewer | Live pathway diagram embeds in-page |
| 4 | mapper | Pick High confidence → Submit | Modal confirms; *"This goes to admin queue, not the public API."* |
| 5 | `/admin/proposals` | Approve the proposal | *"Audit trail records both proposer and approver — OAuth-prefixed identities."* |
| 6 | `/explore` | KE-WP tab → search "inflammation" → show row | *"Search and sort all client-side over our REST API. ~123 approved mappings live today."* |
| 7 | `/api/docs` | Swagger → run `GET /api/v1/mappings?ke_id=KE+149` | JSON payload; *"This is exactly what the molAOP-Analyser pulls in."* |
| 8 | `/downloads` | Show GMT + RDF/TTL exports | *"FAIR by design — fgsea/clusterProfiler-ready GMTs and an RDF graph for SPARQL federation."* |

If asked about scoring details mid-demo, jump to
`/documentation/scoring-guide` — the page has been pruned to current
v1.5 content only (BioBERT ranker + confidence rubric). No legacy
hybrid material remains there to confuse the audience.

## If something breaks

| Symptom | Recovery |
|---------|----------|
| Suggestion spinner hangs | Switch to KE 1825 backup tab; comment on cold-cache embedding warm-up |
| OAuth login fails on stage | Use the **guest login** flow (workshop access codes) |
| Network flaky | Flip to the screenshot folder; narrate without the live tool |
| Banner pops back up | Dismiss inline; *"we surface change banners on UI updates so curators are never surprised"* |
| Form rejects submission | The fixes shipped today (`9793013`, `531299a`, `efeb076`) cover the known cases — if a new one shows up, skip the submit step and continue at step 6 |

## Talking points to weave in

- **v1.5 pure-semantic ranking** just landed (this week): *"We separated
  ranking signal from informational metadata. BioBERT decides order;
  shared genes inform the curator."*
- **End-to-end story**: the Builder produces curated mappings; the sister
  **Molecular AOP Analyser** (https://molaop-analyser.vhp4safety.nl)
  consumes them for KE-level enrichment of gene-expression data.
- **FAIR exports**: GMT for fgsea/clusterProfiler, RDF/TTL for SPARQL,
  CSV/JSON for everything else. Public REST API. No login needed to
  read.
- **Multi-provider OAuth** (GitHub, ORCID, LS Login, SURFconext) — so
  curators can sign in with whatever institutional identity they
  already use.
- **Curator-in-the-loop**, not LLM-in-the-loop: every approved mapping
  is a human decision backed by a structured 4-question rubric.

## Numbers to know (as of 2026-05-10)

- 123 approved KE-WP mappings live; 79 high-confidence.
- ~1,561 AOP-Wiki Key Events addressable.
- Top-mapped KEs (good fall-backs): KE 1395 (Liver Cancer), KE 89, KE 115, KE 149.
- Public-API rate limit: 100 req/h/IP (multi-process; effective higher).

## Recommended demo KE: KE 149 — "Increase, Inflammation"

- 9 AOPs, mapped to **WP453 Inflammatory response pathway** at high confidence.
- Universally recognised by a mixed audience.
- Strong AOP-context graph, credible suggestion list.

Backup: **KE 1825 — "Increase, Cell death"** (12 AOPs, more dramatic).

## What NOT to demo

- The Reactome tab beyond a quick mention — it carries an explicit
  "under development" banner. Phase 30 (Reactome parity tuning) is
  queued, not started.
- `/dataset/citation`, `/dataset/datacite`, `/dataset/versions` — these
  routes need Zenodo/DataCite credentials that aren't provisioned;
  they may 500.
- `/confidence_assessment` — dead route slated for Phase 33 cleanup.
