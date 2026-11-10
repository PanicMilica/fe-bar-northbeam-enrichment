# Evidence 6 · Lakebase: operational serving and the analyst feedback loop (executed)
Notebook: [src/lakebase/02_lakebase_sync_reviews.py](../src/lakebase/02_lakebase_sync_reviews.py), job task `apply_reviews_and_sync`.

## The instance and the synced table
* Lakebase instance `northbeam-enrichment`: **AVAILABLE**, capacity CU_1, Postgres 16; registered in Unity Catalog as `northbeam_lakebase`.
* Synced table `northbeam_lakebase.public.gold_product_enrichment` ← `milica_test.fe_bar_northbeam.gold_product_enrichment`
  (primary key market + item_id, scheduling policy TRIGGERED, refreshed by the job after every run): **SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE**.
* `review.review_decisions` (Postgres, BIGSERIAL id, CHECK action IN approve/correct/reject): written by the app.

## What the app reads (Postgres, after week 42)
| market | products | waiting_for_review | human_verified | last_update |
|---|---|---|---|---|
| ES | 271 | 100 | 3 | 2026-11-10 17:29:43 UTC |
| US | 282 | 105 | 0 | 2026-11-10 17:29:43 UTC |

Point lookup by primary key (50 random products, from a laptop over the internet): median **138 ms**, p95 144 ms.

## The loop, end to end: analyst in the app → Postgres → job → Unity Catalog gold → Postgres
**Step 1: an analyst saved decisions on 3 products in the app (Postgres rows, before the week 41 job):**
| decision_id | item | action | field | ai_value | corrected_value | reviewer_email | reviewed_at (UTC) |
|---|---|---|---|---|---|---|---|
| 1 | ES-100000 | approve | segment | ENERGY | ENERGY | analyst@northbeam.example | 17:14:28 |
| 2 | ES-100015 | correct | segment | | HIGH PROTEIN | analyst@northbeam.example | 17:15:15 |
| 3 | ES-100015 | correct | protein_g_per_bar | | 16.0 | analyst@northbeam.example | 17:15:15 |
| 4 | ES-100015 | correct | kcal_per_bar | | 150.0 | analyst@northbeam.example | 17:15:15 |
| 5 | ES-100019 | reject | segment | | | analyst@northbeam.example | 17:15:27 |

**Step 2: job output of task `apply_reviews_and_sync` (week 41 run 843351037895198), copied verbatim:**
```text
5 pending analyst decisions
 decision_id market   item_id  action             field ai_value corrected_value ... reviewer_email
           1     ES ES-100000 approve           segment   ENERGY          ENERGY ... analyst@northbeam.example
           2     ES ES-100015 correct           segment     None    HIGH PROTEIN ... analyst@northbeam.example
           3     ES ES-100015 correct protein_g_per_bar      nan            16.0 ... analyst@northbeam.example
           4     ES ES-100015 correct      kcal_per_bar      nan           150.0 ... analyst@northbeam.example
           5     ES ES-100019  reject           segment     None            None ... analyst@northbeam.example
```
| market | item_id | segment | protein_g_per_bar | kcal_per_bar | confidence_score | reviewed_by |
|---|---|---|---|---|---|---|
| ES | ES-100019 | | | | 100 | analyst@northbeam.example |
| ES | ES-100015 | HIGH PROTEIN | 16.0 | 150.0 | 100 | analyst@northbeam.example |
| ES | ES-100000 | ENERGY | 5.5 | 369.0 | 100 | analyst@northbeam.example |
```text
synced table refresh: COMPLETED
SyncedTableState.SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE
```
**Step 3: the decisions are now marked `applied = True` in Postgres**, copied into the governed UC table `review_history`
(row filter + masked reviewer), and the app shows the 3 products as human verified after the sync.

## Least privilege for the app's service principal (Postgres grants)
| grantee | schema.table | privileges |
|---|---|---|
| app service principal | public.gold_product_enrichment | SELECT |
| app service principal | review.review_decisions | INSERT, SELECT |
