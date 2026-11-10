# Job run 68227308960061 (2026W42_incremental)

Job: `[dev milica_panic] northbeam_weekly_enrichment` · result: **SUCCESS** · run page: https://<workspace-url>

| task | result | duration (s) | evidence |
|---|---|---|---|
| ingest | SUCCESS | 136 | Lakeflow pipeline update (see [../../lakeflow_pipeline.md](../../lakeflow_pipeline.md)) |
| setup_and_governance | SUCCESS | 19 | [setup_and_governance.md](setup_and_governance.md) |
| enrich | SUCCESS | 132 | [enrich.md](enrich.md) |
| apply_reviews_and_sync | SUCCESS | 90 | [apply_reviews_and_sync.md](apply_reviews_and_sync.md) |
| evaluate | SUCCESS | 64 | [evaluate.md](evaluate.md) |

## Evaluate task output (notebook exit value)
```json
[{"products":553,"automation_rate":0.6292947559,"auto_precision":1.0,"auto_protein_within_1g":0.9971014493,"match_accuracy_all":0.9294755877,"kcal_mae_when_matched":0.0123752495,"protein_mae_when_matched":0.0001996008,"wrong_matches_caught_by_review":1.0}]
```