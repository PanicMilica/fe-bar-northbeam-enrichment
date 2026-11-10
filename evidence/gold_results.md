# Gold results: enriched products and KPIs
_Collected 2026-11-10 17:42 UTC from workspace <workspace> (SQL warehouse 148ccb90800933a1)._

## KPIs from the metric view (as Genie and the app see them)

```sql
SELECT market, MEASURE(products) AS products, MEASURE(automation_rate) AS automation_rate,
       MEASURE(attribute_coverage) AS attribute_coverage, MEASURE(products_needing_review) AS needs_review,
       MEASURE(human_verified_products) AS human_verified, MEASURE(high_protein_share) AS high_protein_share
FROM milica_test.fe_bar_northbeam.mv_enrichment_kpis GROUP BY market ORDER BY market
```

| market | products | automation_rate | attribute_coverage | needs_review | human_verified | high_protein_share |
|---|---|---|---|---|---|---|
| ES | 271 | 0.6309963099630996 | 0.933579335793358 | 100 | 3 | 0.2551440329218107 |
| US | 282 | 0.6276595744680851 | 0.9716312056737588 | 105 | 0 | 0.2490272373540856 |

## Segment mix

```sql
SELECT market, coalesce(segment, 'UNRESOLVED') AS segment, count(*) AS products, round(avg(confidence_score), 1) AS avg_confidence
FROM milica_test.fe_bar_northbeam.gold_product_enrichment GROUP BY ALL ORDER BY market, products DESC
```

| market | segment | products | avg_confidence |
|---|---|---|---|
| ES | NOURISH | 100 | 73.7 |
| ES | HIGH PROTEIN | 62 | 70.1 |
| ES | NOT A SNACK BAR | 28 | 72.2 |
| ES | DIET | 26 | 77.2 |
| ES | TREAT | 25 | 77.1 |
| ES | ENERGY | 15 | 69.0 |
| ES | UNRESOLVED | 15 | 6.7 |
| US | NOURISH | 82 | 75.0 |
| US | HIGH PROTEIN | 64 | 72.0 |
| US | TREAT | 37 | 65.5 |
| US | DIET | 33 | 74.9 |
| US | ENERGY | 33 | 70.0 |
| US | NOT A SNACK BAR | 25 | 80.1 |
| US | UNRESOLVED | 8 | 0.0 |

## Sample: auto-enriched products (high confidence)

```sql
SELECT market, item_id, descriptor, descriptor_en, evidence_tier, kcal_per_bar, protein_g_per_bar, segment, claimed_ingredient, confidence_score
FROM milica_test.fe_bar_northbeam.gold_product_enrichment WHERE NOT needs_review AND NOT human_verified ORDER BY confidence_score DESC, item_id LIMIT 10
```

| market | item_id | descriptor | descriptor_en | evidence_tier | kcal_per_bar | protein_g_per_bar | segment | claimed_ingredient | confidence_score |
|---|---|---|---|---|---|---|---|---|---|
| ES | ES-100005 | BARR C/ PROT SAB CHOC NEGRO ENERVIT SPA 60G 3UN | BARR C/ PROT SAB CHOC NEGRO ENERVIT SPA 60G 3UN | barcode_exact | 225.6 | 19.8 | HIGH PROTEIN | PROTEIN BLEND | 90 |
| ES | ES-100006 | BARR DE CHOC BLANCO MERCADONA 21G 6UN | WHITE CHOCOLATE BAR MERCADONA 21G 6UN | barcode_exact | 90.0 | 1.1 | TREAT | CHOCOLATE | 90 |
| ES | ES-100009 | PROTEIN BAR SOFT CARAMEL FOODSPRING 65G 1UN | Protein Bar Soft Caramel Foodspring 65g 1 Unit | barcode_exact | 226.2 | 18.9 | HIGH PROTEIN | PROTEIN BLEND | 90 |
| ES | ES-100010 | BUDDHA ENERGY ISWARI 35G 1UN | BUDDHA ENERGY ISWARI 35G 1UN | barcode_exact | 140.0 | 3.1 | NOURISH | FRUIT | 90 |
| ES | ES-100011 | 30% PROTEIN BARS CHOC JUST LOADING 30G 1UN | 30% Protein Bars Chocolate Just Loading 30g 1 Unit | barcode_exact | 108.6 | 9.0 | DIET | PROTEIN BLEND | 90 |
| ES | ES-100018 | SNACK DE CHOC BLANCO Y TROCITOS DE FRUTOS ROJOS BICENTURY 18G 1UN | White Chocolate Snack with Red Fruit Pieces Bicentury 18g 1unit | barcode_exact | 90.7 | 1.1 | TREAT | CHOCOLATE | 90 |
| ES | ES-100054 | MUESLY CHOC C/ LCH HERO 25G 1UN | MUESLY CHOC C/ LCH HERO 25G 1UN | barcode_exact | 113.8 | 1.7 | NOT A SNACK BAR | CHOCOLATE | 90 |
| ES | ES-100057 | TRAIL MIX NATURE VALLEY 35G 1UN | TRAIL MIX NATURE VALLEY 35G 1UN | barcode_exact | 157.5 | 1.1 | NOURISH | OATS | 90 |
| ES | ES-100062 | BARR DE PROT SAB CHOC BLANCO WEIDER 35G 1UN | WEIDER White Chocolate Protein Bar 35g 1 unit | barcode_exact | 141.4 | 9.4 | DIET | PROTEIN BLEND | 90 |
| ES | ES-100066 | SWEET SALTY NUT NATURE VALLEY 30G 1UN | SWEET SALTY NUT NATURE VALLEY 30G 1UN | barcode_exact | 139.3 | 0.0 | NOURISH | NUTS | 90 |

## Sample: name-matched private label (GenAI tier) with explanation

```sql
SELECT market, item_id, descriptor_en, matched_product_name, protein_g_per_bar, segment, confidence_score, needs_review, explanation
FROM milica_test.fe_bar_northbeam.gold_product_enrichment WHERE evidence_tier = 'name_match' ORDER BY confidence_score DESC LIMIT 8
```

| market | item_id | descriptor_en | matched_product_name | protein_g_per_bar | segment | confidence_score | needs_review | explanation |
|---|---|---|---|---|---|---|---|---|
| ES | ES-100000 | RED FRUITS CARREFOUR FRANCE 100G 1UNIT | Frutos rojos | 5.5 | ENERGY | 100 | false | HUMAN VERIFIED (approve). Previous: Per bar: 5.5 g protein, 369 kcal, positioning 'wholesome' -> 5-14 g protein and more than 200 kcal per b |
| ES | ES-100082 | BUDDHA ENERGY ACAI BANANA STRAWBERRY 35G 1UN | Buddha Energy - Acai, Banana & Strawberry | 2.7 | NOURISH | 74 | false | Per bar: 2.7 g protein, 128.4 kcal, positioning 'fruit_nut' -> Under 200 kcal, fruit and/or nut based. The retailer descriptor matches the c |
| ES | ES-100107 | NUTRAMINO Sweet Coconut Bar 66g NUTRAMINO 66g 1 unit | Nutramino Sweet Coconutbar 66g | 20.5 | HIGH PROTEIN | 74 | false | Per bar: 20.5 g protein, 285.8 kcal, positioning 'indulgent' -> 15 g or more protein per bar. The retailer record exactly matches Nutramino  |
| US | US-100120 | NOCOW PROTEIN BAR 2.12OZ 1CT | protein bar | 20.0 | HIGH PROTEIN | 74 | false | Per bar: 20 g protein, 190 kcal, positioning 'diet' -> 15 g or more protein per bar. The retailer record is for nocow Protein Bar 2.12 oz 1c |
| US | US-100076 | EAT NATURAL DARK CHOCOLATE & SEA SALT FRUIT & NUT BAR 1.41OZ 1CT | Dark Chocolate &amp; Sea Salt Fruit &amp; Nut Bar | 3.4 | TREAT | 74 | false | Per bar: 3.4 g protein, 175 kcal, positioning 'indulgent' -> Indulgent / confectionery-like positioning (chocolate coated, marshmallow, cand |
| US | US-100103 | POWER CRUNCH PROTEIN ENERGY BAR FRENCH VANILLA CRÈME 1.41OZ 1CT | power crunch Protein Energy Bar french vanilla crème | 13.0 | DIET | 74 | false | Per bar: 13 g protein, 220 kcal, positioning 'diet' -> Positioned for weight control / meal replacement / calorie control (e.g. "control", " |
| US | US-100032 | SIMPLY NATURE STRAWBERRY GRANOLA BITES 0.85OZ 5CT | Strawberry Granola Bites | 2.0 | NOURISH | 74 | false | Per bar: 2 g protein, 100 kcal, positioning 'wholesome' -> Under 200 kcal, not fruit/nut based (cereal, oat, grain bars etc.). The retailer  |
| US | US-100019 | QUEST APPLE PIE BAR 2.12OZ 1CT | Quest Apple Pie Bar | 20.0 | HIGH PROTEIN | 74 | false | Per bar: 20 g protein, 169.8 kcal, positioning 'diet' -> 15 g or more protein per bar. The retailer record says Quest Apple Pie Bar 2.12oz 1 |

## Sample: sent to analyst review (lowest confidence)

```sql
SELECT market, item_id, descriptor_en, evidence_tier, confidence_score, confidence_factors, explanation
FROM milica_test.fe_bar_northbeam.gold_product_enrichment WHERE needs_review AND NOT human_verified ORDER BY confidence_score LIMIT 8
```

| market | item_id | descriptor_en | evidence_tier | confidence_score | confidence_factors | explanation |
|---|---|---|---|---|---|---|
| US | US-900002 | FRUIT & NUT BAR ALMOND 30G 4CT | none | 0 | {"evidence": "none"} | No public product matched with enough certainty: sent to analyst review. The retailer item is a private-label fruit & nut bar with almond, w |
| US | US-100095 | PROTEIN BAR 1.41OZ 1CT | none | 0 | {"evidence": "none"} | No public product matched with enough certainty: sent to analyst review. The descriptor is a generic private-label protein bar with no brand |
| ES | ES-900003 | BARR PUFFED RICE WITH MILK 25G 6UN | none | 0 | {"evidence": "none"} | No public product matched with enough certainty: sent to analyst review. The retailer description translates to a puffed rice cereal bar wit |
| ES | ES-100074 | Cereal Bars with Grains and Almonds Carrefour France 25g 4 Units | name_match | 0 | {"source": 0.75, "identity": 0.88, "agreement": 1.0, "margin": 1.0, "completeness": 1.0, "judge": 0.0, "fallback": 1.0} | Per bar: 4 g protein, 127 kcal, positioning 'wholesome' -> Under 200 kcal, not fruit/nut based (cereal, oat, grain bars etc.). The retailer  |
| ES | ES-100240 | BAR OF WAX WITH STRAWBERRY AND WHITE CHOCOLATE 25G 1 UNIT | none | 0 | {"evidence": "none"} | No public product matched with enough certainty: sent to analyst review. The retailer text describes a 25 g bar with strawberry and white ch |
| ES | ES-100239 | BLACK CHOCOLATE 21G 6UN | none | 0 | {"evidence": "none"} | Not a snack bar (e.g. biscuit or cookie): snack-bar segmentation not applicable. The retailer item is a private-label dark chocolate product |
| US | US-900003 | CRISPY RICE MARSHMALLOW BAR 35G 5CT | none | 0 | {"evidence": "none"} | No public product matched with enough certainty: sent to analyst review. The retailer item is a crispy rice marshmallow bar, which suggests  |
| ES | ES-100147 | Oat Muesli with Cranberries and Pumpkin Seeds Hero 35g 1unit | none | 0 | {"evidence": "none"} | Not a snack bar (e.g. biscuit or cookie): snack-bar segmentation not applicable. This retailer item is an oat muesli with cranberries and pu |

## Human-in-the-loop: analyst decisions applied to gold

```sql
SELECT market, item_id, segment, protein_g_per_bar, kcal_per_bar, confidence_score, human_verified, explanation
FROM milica_test.fe_bar_northbeam.gold_product_enrichment WHERE human_verified
```

| market | item_id | segment | protein_g_per_bar | kcal_per_bar | confidence_score | human_verified | explanation |
|---|---|---|---|---|---|---|---|
| ES | ES-100019 |  |  |  | 100 | true | HUMAN REJECTED the AI match. |
| ES | ES-100015 | HIGH PROTEIN | 16.0 | 150.0 | 100 | true | HUMAN VERIFIED (correct). Previous: No public product matched with enough certainty: sent to analyst review. The retailer record is for an E |
| ES | ES-100000 | ENERGY | 5.5 | 369.0 | 100 | true | HUMAN VERIFIED (approve). Previous: Per bar: 5.5 g protein, 369 kcal, positioning 'wholesome' -> 5-14 g protein and more than 200 kcal per b |

## Review history (governed: row filter + masked reviewer)

```sql
SELECT market, item_id, action, field, ai_value, corrected_value, reviewer_email, reviewed_at, applied_at FROM milica_test.fe_bar_northbeam.review_history ORDER BY reviewed_at
```

| market | item_id | action | field | ai_value | corrected_value | reviewer_email | reviewed_at | applied_at |
|---|---|---|---|---|---|---|---|---|
| ES | ES-100000 | approve | segment | ENERGY | ENERGY | analyst@northbeam.example | 2026-11-10T12:14:28.907-05:00 | 2026-11-10T12:21:54.406-05:00 |
| ES | ES-100015 | correct | segment |  | HIGH PROTEIN | analyst@northbeam.example | 2026-11-10T12:15:15.246-05:00 | 2026-11-10T12:21:54.406-05:00 |
| ES | ES-100015 | correct | protein_g_per_bar | nan | 16.0 | analyst@northbeam.example | 2026-11-10T12:15:15.304-05:00 | 2026-11-10T12:21:54.406-05:00 |
| ES | ES-100015 | correct | kcal_per_bar | nan | 150.0 | analyst@northbeam.example | 2026-11-10T12:15:15.352-05:00 | 2026-11-10T12:21:54.406-05:00 |
| ES | ES-100019 | reject | segment |  |  | analyst@northbeam.example | 2026-11-10T12:15:27.811-05:00 | 2026-11-10T12:21:54.406-05:00 |

## Run metrics per weekly delivery (incremental: only new products are enriched)

```sql
SELECT delivery_week, market, products, barcode_exact, name_match, no_evidence, llm_calls, est_cost_usd, cost_per_1000_usd,
       runtime_s, avg_confidence, review_rate, analyst_hours_saved FROM milica_test.fe_bar_northbeam.run_metrics ORDER BY created_at
```

| delivery_week | market | products | barcode_exact | name_match | no_evidence | llm_calls | est_cost_usd | cost_per_1000_usd | runtime_s | avg_confidence | review_rate | analyst_hours_saved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026W40 | ES | 230 | 178 | 38 | 14 | 460 | 0.1502 | 0.65 | 143.0 | 68.2 | 0.374 | 14.4 |
| 2026W40 | US | 230 | 174 | 48 | 8 | 460 | 0.1502 | 0.65 | 143.0 | 70.9 | 0.361 | 14.7 |
| 2026W41 | ES | 18 | 13 | 4 | 1 | 36 | 0.0118 | 0.66 | 87.5 | 65.6 | 0.5 | 0.9 |
| 2026W41 | US | 20 | 14 | 6 | 0 | 40 | 0.0132 | 0.66 | 87.5 | 68.2 | 0.45 | 1.1 |
| 2026W42 | ES | 23 | 18 | 3 | 2 | 46 | 0.0146 | 0.64 | 85.7 | 70.5 | 0.348 | 1.5 |
| 2026W42 | US | 32 | 25 | 7 | 0 | 64 | 0.0203 | 0.64 | 85.7 | 71.5 | 0.406 | 1.9 |

## Evaluation results history (MLflow run ids)

```sql
SELECT * FROM milica_test.fe_bar_northbeam.evaluation_results
```

| products | automation_rate | auto_precision | auto_protein_within_1g | match_accuracy_all | kcal_mae_when_matched | protein_mae_when_matched | wrong_matches_caught_by_review | mlflow_run_id |
|---|---|---|---|---|---|---|---|---|
| 553 | 0.6292947558770343 | 1.0 | 0.9971014492753624 | 0.9294755877034359 | 0.01237524950099798 | 1.996007984031938E-4 | 1.0 | 819c682965764ea98efbf75d84a56970 |
| 460 | 0.6326086956521739 | 1.0 | 0.9965635738831615 | 0.9282608695652174 | 0.014939759036144551 | 2.4096385542168695E-4 | 1.0 | 906571b824f840ebad2d2a426b4b9f89 |
| 553 | 0.6292947558770343 | 1.0 | 0.9971014492753624 | 0.9294755877034359 | 0.01237524950099798 | 1.996007984031938E-4 | 1.0 | fb880d4e1619424684d8d1c7d635dab8 |
| 498 | 0.6305220883534136 | 1.0 | 0.9967845659163987 | 0.927710843373494 | 0.013808463251670353 | 2.2271714922049017E-4 | 1.0 | 256fbc4ca8d4496790ab4b0cdd28995b |
