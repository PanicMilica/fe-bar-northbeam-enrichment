# Job run 843351037895198 (2026W41_reviews_applied_incremental)

Job: `[dev milica_panic] northbeam_weekly_enrichment` · result: **SUCCESS** · run page: https://<workspace-url>

| task | result | duration (s) | evidence |
|---|---|---|---|
| ingest | SUCCESS | 125 | Lakeflow pipeline update (see [../../lakeflow_pipeline.md](../../lakeflow_pipeline.md)) |
| setup_and_governance | SUCCESS | 22 | [setup_and_governance.md](setup_and_governance.md) |
| enrich | SUCCESS | 136 | [enrich.md](enrich.md) |
| apply_reviews_and_sync | SUCCESS | 124 | [apply_reviews_and_sync.md](apply_reviews_and_sync.md) |
| evaluate | SUCCESS | 54 | [evaluate.md](evaluate.md) |

## Evaluate task output (notebook exit value)
```json
[{"products":498,"automation_rate":0.6305220884,"auto_precision":1.0,"auto_protein_within_1g":0.9967845659,"match_accuracy_all":0.9277108434,"kcal_mae_when_matched":0.0138084633,"protein_mae_when_matched":0.0002227171,"wrong_matches_caught_by_review":1.0}]
```