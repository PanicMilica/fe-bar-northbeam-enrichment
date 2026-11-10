# Lakeflow Declarative Pipeline: raw retailer deliveries + public product reference -> silver.
#
#  landing/<market>/<week>/*.csv ──Auto Loader──> bronze_delivery_<market>  (raw, per-market schema)
#                                                   │ standardise + expectations
#                                                   ▼
#                                     v_delivery_items ──AUTO CDC (SCD1)──> silver_product_item
#
#  public_reference/*.jsonl ──Auto Loader──> bronze_public_reference ──> silver_public_reference
#
# New deliveries are picked up incrementally (Auto Loader checkpoints), so a weekly
# refresh only reads the new file. AUTO CDC keeps one row per market + item and
# records the first and last week an item was seen.

import sys

import dlt
import pandas as pd
import yaml
from pyspark.sql import functions as F, types as T

SRC = spark.conf.get("bundle.sourcePath")
sys.path.append(SRC)
from enrichment_lib.normalize import to_gtin13, unit_weight_g  # noqa: E402

CATALOG = spark.conf.get("catalog")
SCHEMA = spark.conf.get("schema")
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/landing"
REFERENCE = f"/Volumes/{CATALOG}/{SCHEMA}/public_reference"
MARKETS = yaml.safe_load(open(f"{SRC}/../config/markets.yml"))
MARKET_CODES = [m for m in MARKETS if m != "non_public_barcode_values"]


# ---------------------------------------------------------------------------
# Bronze: one streaming table per market, raw columns kept as delivered
# ---------------------------------------------------------------------------
def bronze_delivery(market: str):
    cfg = MARKETS[market]

    @dlt.table(
        name=f"bronze_delivery_{market.lower()}",
        comment=f"Raw weekly product deliveries for {market}, exactly as received (Auto Loader).",
        table_properties={"quality": "bronze"},
    )
    def _bronze():
        return (
            spark.readStream.format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", True)
            .option("cloudFiles.inferColumnTypes", False)   # keep barcodes as strings (leading zeros)
            .option("cloudFiles.schemaEvolutionMode", "rescue")
            .option("pathGlobFilter", cfg["file_glob"])
            .load(f"{LANDING}/{market}/")
            .withColumn("_source_file", F.col("_metadata.file_path"))
            .withColumn("_ingested_at", F.current_timestamp())
        )


for _m in MARKET_CODES:
    bronze_delivery(_m)


# ---------------------------------------------------------------------------
# Standardise: map each market to one schema, normalise barcodes and pack size
# ---------------------------------------------------------------------------
@F.pandas_udf(T.StringType())
def gtin13_udf(raw: pd.Series, fmt: pd.Series) -> pd.Series:
    return pd.Series([to_gtin13(r, f) for r, f in zip(raw, fmt)])


@F.pandas_udf(T.DoubleType())
def unit_weight_udf(size: pd.Series, count: pd.Series) -> pd.Series:
    return pd.Series([unit_weight_g(s, c) for s, c in zip(size, count)], dtype="float64")


@dlt.view(name="v_delivery_items", comment="All markets mapped to the standard product schema.")
@dlt.expect_or_drop("valid_item_id", "item_id IS NOT NULL")
@dlt.expect_or_drop("valid_week", "delivery_week RLIKE '^[0-9]{4}W[0-9]{2}$'")
@dlt.expect("has_descriptor", "descriptor IS NOT NULL AND length(descriptor) > 5")
@dlt.expect("public_barcode", "gtin13 IS NOT NULL")   # warn only: private label is expected
def v_delivery_items():
    frames = []
    for market in MARKET_CODES:
        cfg, c = MARKETS[market], MARKETS[market]["columns"]
        frames.append(
            dlt.read_stream(f"bronze_delivery_{market.lower()}").select(
                F.lit(market).alias("market"),
                F.col(c["item_id"]).alias("item_id"),
                F.col(c["barcode"]).alias("barcode_raw"),
                F.lit(cfg["barcode_format"]).alias("barcode_format"),
                F.col(c["descriptor"]).alias("descriptor"),
                F.lit(cfg["source_language"]).alias("source_language"),
                F.nullif(F.col(c["brand"]), F.lit("PRIVATE LABEL")).alias("brand"),
                (F.col(c["brand"]) == "PRIVATE LABEL").alias("is_private_label"),
                F.col(c["manufacturer"]).alias("manufacturer"),
                F.col(c["size_text"]).alias("size_text"),
                F.col(c["pack_count_text"]).alias("pack_count_text"),
                F.col("DELIVERY_WEEK").alias("delivery_week"),
                F.col("_source_file"),
            )
        )
    df = frames[0]
    for f in frames[1:]:
        df = df.unionByName(f)
    return (df.withColumn("gtin13", gtin13_udf("barcode_raw", "barcode_format"))
              .withColumn("unit_weight_g", unit_weight_udf("size_text", "pack_count_text")))


# ---------------------------------------------------------------------------
# Silver: one row per market + item (AUTO CDC, SCD type 1)
# ---------------------------------------------------------------------------
dlt.create_streaming_table(
    name="silver_product_item",
    comment="Standardised product master across markets: one row per market + item, latest delivery wins.",
    table_properties={"quality": "silver", "delta.enableChangeDataFeed": "true"},
)
dlt.create_auto_cdc_flow(
    target="silver_product_item",
    source="v_delivery_items",
    keys=["market", "item_id"],
    sequence_by=F.col("delivery_week"),
    stored_as_scd_type=1,
)


@dlt.table(
    name="silver_item_first_seen",
    comment="First and last delivery week per item; drives the 'new products only' worklist.",
    table_properties={"quality": "silver"},
)
def silver_item_first_seen():
    items = None
    for market in MARKET_CODES:
        c = MARKETS[market]["columns"]
        df = dlt.read(f"bronze_delivery_{market.lower()}").select(
            F.lit(market).alias("market"), F.col(c["item_id"]).alias("item_id"), F.col("DELIVERY_WEEK").alias("week"))
        items = df if items is None else items.unionByName(df)
    return items.groupBy("market", "item_id").agg(
        F.min("week").alias("first_seen_week"), F.max("week").alias("last_seen_week"),
        F.countDistinct("week").alias("weeks_seen"))


# ---------------------------------------------------------------------------
# Public product reference (Open Food Facts snapshot, ODbL)
# ---------------------------------------------------------------------------
@dlt.table(name="bronze_public_reference",
           comment="Public Open Food Facts snapshot of snack bars (ODbL), as downloaded.",
           table_properties={"quality": "bronze"})
def bronze_public_reference():
    return (spark.readStream.format("cloudFiles").option("cloudFiles.format", "json")
            .option("pathGlobFilter", "*.jsonl").load(REFERENCE)
            .withColumn("_ingested_at", F.current_timestamp()))


@dlt.table(name="silver_public_reference",
           comment="Cleaned public product reference: one row per GTIN with per-100 g and per-serving nutrition.",
           table_properties={"quality": "silver"})
@dlt.expect_or_drop("valid_gtin", "gtin13 IS NOT NULL AND length(gtin13) = 13")
@dlt.expect_or_drop("has_nutrition", "kcal_100g IS NOT NULL AND protein_100g IS NOT NULL")
@dlt.expect_or_drop("plausible_nutrition", "kcal_100g BETWEEN 50 AND 700 AND protein_100g BETWEEN 0 AND 100")
def silver_public_reference():
    serving = F.col("serving_quantity").cast("double")
    pack_g = F.regexp_extract(F.lower("quantity"), r"(\d+(?:[.,]\d+)?)\s*(g|gr)\b", 1)
    pack_g = F.regexp_replace(pack_g, ",", ".").cast("double")
    return (dlt.read("bronze_public_reference")
            .select(
                F.lpad("code", 13, "0").alias("gtin13"),
                F.coalesce(F.col("product_name_en"), F.col("product_name")).alias("product_name"),
                F.col("product_name").alias("product_name_original"),
                F.split("brands", ",")[0].alias("brand"),
                F.col("quantity").alias("pack_quantity"),
                F.when((serving > 5) & (serving <= 120), serving)
                 .when(pack_g <= 80, pack_g).alias("serving_g"),
                F.col("kcal_100g").cast("double").alias("kcal_100g"),
                F.col("protein_100g").cast("double").alias("protein_100g"),
                F.col("sugars_100g").cast("double").alias("sugars_100g"),
                F.col("kcal_serving").cast("double").alias("kcal_serving"),
                F.col("protein_serving").cast("double").alias("protein_serving"),
                F.col("ingredients_text"),
                F.col("categories_tags"),
                F.col("query_country").alias("source_country"),
            )
            .withColumn("search_name", F.concat_ws(" ", "brand", "product_name"))
            .dropDuplicates(["gtin13"]))
