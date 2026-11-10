# Lakebase evidence: operational serving for the review app
_Collected 2026-11-10 17:45 UTC._

Instance `northbeam-enrichment`: state **AVAILABLE**, capacity CU_1, PG_VERSION_16.
Synced table `northbeam_lakebase.public.gold_product_enrichment` ← `milica_test.fe_bar_northbeam.gold_product_enrichment`: **SYNCED_TABLE_ONLINE_NO_PENDING_UPDATE**, scheduling policy TRIGGERED.

## Synced gold table in Postgres (what the app reads)
```sql
SELECT market, count(*) AS products,
                                count(*) FILTER (WHERE needs_review AND NOT human_verified) AS waiting_for_review,
                                count(*) FILTER (WHERE human_verified) AS human_verified, max(updated_at) AS last_update
                         FROM public.gold_product_enrichment GROUP BY market ORDER BY market
```

| market | products | waiting_for_review | human_verified | last_update |
|---|---|---|---|---|
| ES | 271 | 100 | 3 | 2026-11-10 17:29:43.878442+00:00 |
| US | 282 | 105 | 0 | 2026-11-10 17:29:43.878442+00:00 |

## Review decisions written by the app (OLTP inserts, applied by the weekly job)
```sql
SELECT decision_id, market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied
                         FROM review.review_decisions ORDER BY decision_id
```

| decision_id | market | item_id | action | field | ai_value | corrected_value | reviewer_email | reviewed_at | applied |
|---|---|---|---|---|---|---|---|---|---|
| 1 | ES | ES-100000 | approve | segment | ENERGY | ENERGY | analyst@northbeam.example | 2026-11-10 17:14:28.907705+00:00 | True |
| 2 | ES | ES-100015 | correct | segment |  | HIGH PROTEIN | analyst@northbeam.example | 2026-11-10 17:15:15.246487+00:00 | True |
| 3 | ES | ES-100015 | correct | protein_g_per_bar | nan | 16.0 | analyst@northbeam.example | 2026-11-10 17:15:15.304630+00:00 | True |
| 4 | ES | ES-100015 | correct | kcal_per_bar | nan | 150.0 | analyst@northbeam.example | 2026-11-10 17:15:15.352134+00:00 | True |
| 5 | ES | ES-100019 | reject | segment |  |  | analyst@northbeam.example | 2026-11-10 17:15:27.811693+00:00 | True |

## Point-lookup latency (primary key, 50 random products, from a laptop over the internet)
median 138.1 ms · p95 143.9 ms · max 275.9 ms

## Grants for the app service principal
```sql
SELECT grantee, table_schema, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
                         FROM information_schema.role_table_grants WHERE grantee NOT IN ('PUBLIC', current_user)
                           AND table_schema IN ('public', 'review') GROUP BY 1, 2, 3 ORDER BY 2, 3
```

| grantee | table_schema | table_name | privileges |
|---|---|---|---|
| databricks_superuser | public | databricks_auth_metrics | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | databricks_list_roles | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | databricks_synced_table_managers | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | gold_product_enrichment | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| <app-service-principal> | public | gold_product_enrichment | SELECT |
| databricks_superuser | public | local_cache | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_backend_perf_counters | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_backpressure_status | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| pg_monitor | public | neon_backpressure_status | SELECT |
| databricks_superuser | public | neon_lfc_stats | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_lwlsn_cache_stats | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_perf_counters | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_relperst_cache_stats | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_relsize_cache_stats | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| databricks_superuser | public | neon_stat_file_cache | DELETE, INSERT, SELECT, TRUNCATE, UPDATE |
| pg_monitor | public | neon_stat_file_cache | SELECT |
| databricks_gateway | review | review_decisions | SELECT |
| databricks_reader_16590 | review | review_decisions | SELECT |
| databricks_superuser | review | review_decisions | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| <app-service-principal> | review | review_decisions | INSERT, SELECT |
