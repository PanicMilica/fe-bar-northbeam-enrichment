# Evidence 5 · Gold results: what the business gets (executed)
Table `milica_test.fe_bar_northbeam.gold_product_enrichment` (553 rows after week 42) and metric view
`mv_enrichment_kpis`. Query results copied from the SQL warehouse, 2026-11-10.

## KPIs (metric view, the same numbers Genie and the app show)
```sql
SELECT market, MEASURE(products), MEASURE(automation_rate), MEASURE(attribute_coverage),
       MEASURE(products_needing_review), MEASURE(human_verified_products), MEASURE(high_protein_share)
FROM milica_test.fe_bar_northbeam.mv_enrichment_kpis GROUP BY market
```
| market | products | automation_rate | attribute_coverage | needs_review | human_verified | high_protein_share |
|---|---|---|---|---|---|---|
| ES | 271 | 0.631 | 0.934 | 100 | 3 | 0.255 |
| US | 282 | 0.628 | 0.972 | 105 | 0 | 0.249 |

## Segment mix (segment rules from config/attributes.yml)
| market | NOURISH | HIGH PROTEIN | DIET | TREAT | ENERGY | NOT A SNACK BAR | UNRESOLVED (to analyst) |
|---|---|---|---|---|---|---|---|
| ES | 100 | 62 | 26 | 25 | 15 | 28 | 15 |
| US | 82 | 64 | 33 | 37 | 33 | 25 | 8 |

## Auto-enriched: exact barcode, Spanish descriptor translated (confidence 90, no analyst needed)
| item | retailer descriptor (as delivered) | descriptor_en (ai_translate) | kcal / bar | protein / bar | segment | ingredient |
|---|---|---|---|---|---|---|
| ES-100005 | BARR C/ PROT SAB CHOC NEGRO ENERVIT SPA 60G 3UN | (kept) | 225.6 | 19.8 | HIGH PROTEIN | PROTEIN BLEND |
| ES-100006 | BARR DE CHOC BLANCO MERCADONA 21G 6UN | WHITE CHOCOLATE BAR MERCADONA 21G 6UN | 90.0 | 1.1 | TREAT | CHOCOLATE |
| ES-100018 | SNACK DE CHOC BLANCO Y TROCITOS DE FRUTOS ROJOS BICENTURY 18G 1UN | White Chocolate Snack with Red Fruit Pieces Bicentury 18g 1unit | 90.7 | 1.1 | TREAT | CHOCOLATE |
| ES-100062 | BARR DE PROT SAB CHOC BLANCO WEIDER 35G 1UN | WEIDER White Chocolate Protein Bar 35g 1 unit | 141.4 | 9.4 | DIET | PROTEIN BLEND |

## Auto-enriched by the GenAI tier: private label, no barcode, resolved by name (confidence 74)
| item | descriptor_en | matched public product | protein / bar | segment | explanation (excerpt) |
|---|---|---|---|---|---|
| US-100019 | QUEST APPLE PIE BAR 2.12OZ 1CT | Quest Apple Pie Bar | 20.0 | HIGH PROTEIN | "Per bar: 20 g protein, 169.8 kcal ... -> 15 g or more protein per bar. The retailer record says Quest Apple Pie Bar 2.12oz ..." |
| ES-100107 | NUTRAMINO Sweet Coconut Bar 66g | Nutramino Sweet Coconutbar 66g | 20.5 | HIGH PROTEIN | "... The retailer record exactly matches Nutramino ..." |
| ES-100082 | BUDDHA ENERGY ACAI BANANA STRAWBERRY 35G 1UN | Buddha Energy - Acai, Banana & Strawberry | 2.7 | NOURISH | "Per bar: 2.7 g protein, 128.4 kcal, positioning 'fruit_nut' -> Under 200 kcal, fruit and/or nut based ..." |

## Sent to an analyst (confidence 0): the AI refuses to guess
| item | descriptor_en | tier | confidence factors | explanation (excerpt) |
|---|---|---|---|---|
| ES-900003 | BARR PUFFED RICE WITH MILK 25G 6UN | none | {"evidence": "none"} | "No public product matched with enough certainty: sent to analyst review. The retailer description translates to a puffed rice cereal bar ..." |
| US-900002 | FRUIT & NUT BAR ALMOND 30G 4CT | none | {"evidence": "none"} | "... a private-label fruit & nut bar with almond ..." |
| ES-100074 | Cereal Bars with Grains and Almonds Carrefour France 25g 4 Units | name_match | {"source": 0.75, "identity": 0.88, ..., **"judge": 0.0**} | the resolver picked a candidate, the **judge model rejected it** → score 0 → review |

## Human-in-the-loop: analyst decisions from the app, applied to gold (week 41 run)
| item | segment | protein / bar | kcal / bar | confidence | human_verified | explanation |
|---|---|---|---|---|---|---|
| ES-100000 | ENERGY | 5.5 | 369.0 | 100 | true | HUMAN VERIFIED (approve). Previous: Per bar: 5.5 g protein, 369 kcal ... |
| ES-100015 | HIGH PROTEIN | 16.0 | 150.0 | 100 | true | HUMAN VERIFIED (correct). Previous: No public product matched with enough certainty ... |
| ES-100019 | (none) | | | 100 | true | HUMAN REJECTED the AI match. |

Later runs (W42 and the re-run) left these three rows untouched: `MERGE ... WHEN MATCHED AND NOT t.human_verified`.
