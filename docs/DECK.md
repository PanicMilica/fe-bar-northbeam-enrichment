# Every new snack bar, enriched the day it arrives
### Northbeam Retail Insights × Databricks · AI product enrichment for category insights
Audience: Chief Data & Product Officer (executive sponsor) · Head of Category Insights (domain owner)

---

## 1. Your clients buy attributes your deliveries don't contain

* Brand clients pay for insights like *"high-protein bars grew 12% in Spain"*.
* Retailer files tell you **what** sold, not **calories and protein per bar** or the **segment**.
* Today analysts research every new product by hand: **~6 minutes per product, ~120 hours every week**.
* The result: a **backlog**, reports that ship **days after** the data, and **private label (12% of items)
  without a barcode** that rarely gets enriched at all.

---

## 2. The outcome, measured on three weekly deliveries (553 products, Spain + US)

| | Today | With Databricks |
|---|---|---|
| Products enriched with no analyst touch | 0% | **63%** |
| Precision of what is enriched automatically | | **100%** |
| Wrong AI matches reaching a client report | | **0** (all caught by review) |
| Delivery → enriched data | days to weeks | **~7 minutes** |
| Model cost per 1,000 products | ~100 analyst hours | **$0.65** |

**At Northbeam scale: ~105 analyst hours per week saved (≈ 3.3 FTE, ~$215k / year), plus ~$300k ARR
potential from a "functional nutrition" report you can now sell for every product.**

---

## 3. What changes for the category team

* Analysts **stop researching and start reviewing**: only the 37% the AI is unsure about.
* Every value comes with **its source, a 0-100 confidence score and a plain-English reason**.
* **Approve / correct / reject in one click** in the review app; decisions are final and never overwritten.
* **You own the definitions**: "High protein = 15 g or more per bar" is a line in a config file, not hidden in a prompt.
* Anyone can ask, in plain English: *"What is the high-protein share in Spain vs the US?"* → 25.5% vs 24.9%.

---

## 4. How it works: one governed loop on one platform

1. **Ingest** each weekly delivery automatically (Lakeflow), with data-quality checks.
2. **Match** each product to a public product database: by barcode first (free), then by name with AI
   (translation + semantic search + an AI judge).
3. **Classify** with *your* rules; the AI never invents a nutrition number.
4. **Serve** results to the review app instantly (Lakebase); analyst decisions flow back into the governed tables.
5. **Ask** in natural language (Genie); every table governed, tagged and auditable (Unity Catalog).

---

## 5. Why you can trust it

* **Precision first:** of 345 products enriched automatically, **345 were correct** against the ground truth.
* **The score means something:** accuracy is 98-100% above confidence 50, and 48% below 30, so the review
  threshold sends the right products to people.
* **Humans have the last word**, and every decision is logged with who made it (visible only to data owners).
* **Explainable:** "Per bar: 27 g protein, 171 kcal → HIGH PROTEIN. Source: 60% Protein Salted Peanut-Caramel (barcode match)."

---

## 6. Proof from the pilot

| Retailer line | What the AI did | Result |
|---|---|---|
| `60% PROTEIN SALTED PEANUT CARAMEL WEIDER 45G 1UN` | barcode match | 27 g / 171 kcal → **HIGH PROTEIN**, confidence 90, auto |
| `QUEST APPLE PIE BAR 2.12OZ 1CT` (private label, no barcode) | name match + AI judge | 20 g / 170 kcal → **HIGH PROTEIN**, confidence 74, auto |
| `BARR F.SECOS Y MIEL 40G 5UN` (store brand, nothing public) | no safe match | **sent to an analyst** with the reason, confidence 0 |

Week 41 and 42: only the **38 and 55 new products** were processed, not the whole catalogue.

---

## 7. Cost and return

| | Per year |
|---|---|
| Analyst time saved | **~$215k** (105 h / week) |
| New report revenue (potential) | **~$300k ARR** |
| Model calls | ~$40 |
| Platform (jobs, Lakebase, app) | est. $5-8k |
| Onboarding a 40,000-item category | **~88% less effort**: weeks instead of a year |

---

## 8. Risks we have already addressed

| Risk | Mitigation |
|---|---|
| Wrong numbers in client reports | AI never writes numbers; precision 100%; uncertain products go to people |
| Private label has no public footprint | Name matching + review; next: retailer web pages and pack images as extra evidence |
| Model changes or price changes | Models are a config setting; evaluation runs every week against a golden set |
| Analysts don't trust it | Reason + source on every value; their corrections are final and measured |

---

## 9. Path to production: 6 weeks

1. **Weeks 1-2:** connect your real delivery landing zone; label 200 products per market as your golden set.
2. **Weeks 3-4:** recalibrate the confidence threshold on your data; roll out the review app to the category team.
3. **Weeks 5-6:** three markets live, weekly runs on file arrival, KPI review with the category team.

**Decision we need today:** approve a production pilot on three markets, with the Head of Category Insights as
owner and success measured as automation rate ≥ 60% at ≥ 99% precision.
