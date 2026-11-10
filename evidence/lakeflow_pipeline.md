# Lakeflow evidence: ingestion pipeline `northbeam_ingest`
_Collected 2026-11-10 17:42 UTC from workspace <workspace> (SQL warehouse 148ccb90800933a1)._

## Pipeline updates (event log)

```sql
SELECT timestamp, details:update_progress.state AS state, origin.update_id
FROM event_log('41577228-1dbb-4d95-b12f-77a559f39726') WHERE event_type = 'update_progress' AND details:update_progress.state IN ('COMPLETED','FAILED')
ORDER BY timestamp
```

| timestamp | state | update_id |
|---|---|---|
| 2026-11-10T10:30:48.479-05:00 | COMPLETED | 26117c3e-6b40-4f4b-946d-3a85338cd4e2 |
| 2026-11-10T10:35:43.377-05:00 | COMPLETED | bcde4294-4809-450d-a040-508055aeff0b |
| 2026-11-10T10:37:35.964-05:00 | COMPLETED | d9ac1fc9-751a-4ca6-b43a-25100e231174 |
| 2026-11-10T10:40:25.767-05:00 | COMPLETED | 05bad115-0a5f-407b-9c30-2f0efdc15a6f |
| 2026-11-10T10:48:47.249-05:00 | COMPLETED | 56f90aca-2132-465e-a956-23d20ca9b51d |
| 2026-11-10T10:50:05.632-05:00 | COMPLETED | 8ea4f184-56e7-4c39-93fb-dd80629835df |
| 2026-11-10T10:57:16.241-05:00 | COMPLETED | 0d455613-4796-4491-b9d8-a8b17fa86998 |
| 2026-11-10T11:03:13.882-05:00 | COMPLETED | a0ea770c-97d6-42a8-a2ce-702e84d2505d |
| 2026-11-10T11:20:04.751-05:00 | COMPLETED | 3bd8bcd3-ef81-4e1c-9809-75300debc223 |
| 2026-11-10T11:25:02.222-05:00 | COMPLETED | a3fcfcd3-678e-4b6e-82ce-d90ec6b6af38 |
| 2026-11-10T12:18:38.642-05:00 | COMPLETED | bad0096b-4e3c-40c2-b14c-6e0e84a7d3a1 |
| 2026-11-10T12:27:17.494-05:00 | COMPLETED | 4f0d9478-2626-4aa7-a4e7-df0f49dec396 |
| 2026-11-10T12:37:10.122-05:00 | COMPLETED | 538e4d97-2f39-4004-9a06-cd4e62d69213 |

## Rows written per flow per update

```sql
SELECT timestamp, origin.flow_name, details:flow_progress.metrics.num_output_rows AS output_rows
FROM event_log('41577228-1dbb-4d95-b12f-77a559f39726')
WHERE event_type = 'flow_progress' AND details:flow_progress.status = 'COMPLETED'
  AND details:flow_progress.metrics.num_output_rows IS NOT NULL
ORDER BY timestamp, origin.flow_name
```

| timestamp | flow_name | output_rows |
|---|---|---|
| 2026-11-10T10:30:29.843-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:30:30.740-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1160 |
| 2026-11-10T10:35:38.748-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1160 |
| 2026-11-10T10:35:43.363-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:37:35.878-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:37:35.899-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1160 |
| 2026-11-10T10:40:25.694-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:40:25.704-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1160 |
| 2026-11-10T10:48:30.768-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:48:32.953-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T10:50:00.186-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T10:50:05.608-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:57:16.167-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T10:57:16.184-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T11:03:09.771-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T11:03:13.827-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T11:20:04.573-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T11:20:04.680-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T11:25:02.154-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 460 |
| 2026-11-10T11:25:02.169-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T12:17:58.304-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T12:18:26.412-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 498 |
| 2026-11-10T12:26:35.948-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T12:27:04.947-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 553 |
| 2026-11-10T12:37:03.276-05:00 | milica_test.fe_bar_northbeam.silver_public_reference | 1155 |
| 2026-11-10T12:37:10.073-05:00 | milica_test.fe_bar_northbeam.silver_item_first_seen | 553 |

## Data quality expectations (passed / failed records)
`public_barcode` is a warn-only expectation: failures are the private-label / missing-barcode items that the GenAI tier resolves.
```sql
SELECT origin.flow_name, e.name AS expectation, e.dataset, sum(e.passed_records) AS passed, sum(e.failed_records) AS failed
FROM event_log('41577228-1dbb-4d95-b12f-77a559f39726'),
     LATERAL explode(from_json(details:flow_progress.data_quality.expectations,
       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) AS t(e)
WHERE event_type = 'flow_progress' AND details:flow_progress.data_quality.expectations IS NOT NULL
GROUP BY ALL ORDER BY 1, 2
```

| flow_name | expectation | dataset | passed | failed |
|---|---|---|---|---|
| milica_test.fe_bar_northbeam.silver_product_item | has_descriptor | v_delivery_items | 1923 | 0 |
| milica_test.fe_bar_northbeam.silver_product_item | public_barcode | v_delivery_items | 1509 | 414 |
| milica_test.fe_bar_northbeam.silver_product_item | valid_item_id | v_delivery_items | 1923 | 0 |
| milica_test.fe_bar_northbeam.silver_product_item | valid_week | v_delivery_items | 1923 | 0 |
| milica_test.fe_bar_northbeam.silver_public_reference | has_nutrition | milica_test.fe_bar_northbeam.silver_public_reference | 15080 | 0 |
| milica_test.fe_bar_northbeam.silver_public_reference | plausible_kcal | milica_test.fe_bar_northbeam.silver_public_reference | 4620 | 20 |
| milica_test.fe_bar_northbeam.silver_public_reference | plausible_nutrition | milica_test.fe_bar_northbeam.silver_public_reference | 10395 | 45 |
| milica_test.fe_bar_northbeam.silver_public_reference | valid_gtin | milica_test.fe_bar_northbeam.silver_public_reference | 15080 | 0 |

## Silver product master: items per market and first-seen week

```sql
SELECT f.market, f.first_seen_week, count(*) AS items, count(s.gtin13) AS with_public_barcode,
       sum(CASE WHEN s.is_private_label THEN 1 ELSE 0 END) AS private_label
FROM milica_test.fe_bar_northbeam.silver_item_first_seen f JOIN milica_test.fe_bar_northbeam.silver_product_item s USING (market, item_id)
GROUP BY ALL ORDER BY 1, 2
```

| market | first_seen_week | items | with_public_barcode | private_label |
|---|---|---|---|---|
| ES | 2026W40 | 230 | 178 | 29 |
| ES | 2026W41 | 18 | 13 | 4 |
| ES | 2026W42 | 23 | 18 | 2 |
| US | 2026W40 | 230 | 187 | 34 |
| US | 2026W41 | 20 | 15 | 4 |
| US | 2026W42 | 32 | 26 | 5 |
