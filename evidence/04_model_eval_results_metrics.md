# Evidence 4 · Evaluation against the golden set (MLflow, executed)
Notebook: [src/eval/03_model_eval.py](../src/eval/03_model_eval.py), job task `evaluate`, logged to MLflow experiment
`/Shared/northbeam_product_enrichment` (latest run `6347fe36a1684fcea71d21492f668eec`).
Ground truth: every synthetic delivery row was generated from a known public product (`data/golden/golden_labels.csv`,
evaluation only, never read by the pipeline). Output below is copied verbatim from the job run (995564116033501).

```text
OVERALL
products                        553.000000
automation_rate                   0.629295     <- share of products that skip analyst review
auto_precision                    1.000000     <- auto-enriched products with the correct product match
auto_protein_within_1g            0.997101
match_accuracy_all                0.929476
kcal_mae_when_matched             0.012375
protein_mae_when_matched          0.000200
wrong_matches_caught_by_review    1.000000     <- every wrong match was routed to an analyst

BY PRODUCT KIND
                 kind  products  match_accuracy  automation_rate  auto_precision  avg_confidence
              branded       439           0.998            0.763             1.0            79.3
 private_label_masked        58           0.638            0.086             1.0            33.4
      barcode_missing        36           0.750            0.139             1.0            50.8
private_label_unknown        20           0.600            0.000             NaN             9.1

CALIBRATION (accuracy per confidence bucket)
confidence_bucket  products  match_accuracy
           90-100       100           0.980
            70-89       248           1.000
            50-69       105           0.990
            30-49        52           0.788
             0-29        48           0.479

RUNS
delivery_week market  products  cost_per_1000_usd  runtime_s  review_rate  analyst_hours_saved
      2026W40     ES       230               0.65      143.0        0.374                 14.4
      2026W40     US       230               0.65      143.0        0.361                 14.7
      2026W41     ES        18               0.66       87.5        0.500                  0.9
      2026W41     US        20               0.66       87.5        0.450                  1.1
      2026W42     ES        23               0.64       85.7        0.348                  1.5
      2026W42     US        32               0.64       85.7        0.406                  1.9

MLflow run: 6347fe36a1684fcea71d21492f668eec
```
Reading it: `private_label_unknown` products do not exist publicly, so "correct" means "no match chosen" (60%); none of
them were auto-enriched, all 20 went to review. The only 2 "incorrect" rows in the 90-100 bucket are analyst-verified rows
(ES-100019 rejected, ES-100015 corrected by hand without a product match), so every auto-enriched row at 90+ is correct.

## How the evaluation changed the design (iterations, measured the same way)
| run | finding | change | result |
|---|---|---|---|
| 1st W40 | kcal error 46 kcal on branded products | per-bar = per-100 g × bar weight (public per-serving fields are inconsistent); drop implausible public records | kcal error **0.01** |
| 1st W40 | 50% of exact-barcode products sent to review although 100% correct | judge weight 0.3 on exact barcode, 1.0 on name match | review rate **36%**, precision still 100% |
| 2nd W40 | 38 correct non-bar products (cookies) in review only because they had no segment | label `NOT A SNACK BAR`, review only if the match is weak | automation 63% |
