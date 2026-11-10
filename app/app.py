"""Northbeam Product Enrichment Console (Databricks App).

For category analysts at Northbeam Retail Insights:
  * Overview      - automation rate, coverage, review backlog and segment mix (Lakebase, millisecond reads)
  * Review queue  - low-confidence products with evidence; approve / correct / reject, written to Lakebase
  * Ask Genie     - natural-language questions over the governed gold tables (Genie Conversation API)

Reads and writes go to Lakebase (Postgres) with the app's service principal and short-lived OAuth
credentials. Decisions are applied back to the Unity Catalog gold table by the weekly job.
"""
import os
import time
import uuid

import pandas as pd
import psycopg
import streamlit as st
from databricks.sdk import WorkspaceClient

st.set_page_config(page_title="Northbeam · Product Enrichment", page_icon="🍫", layout="wide")
w = WorkspaceClient()
INSTANCE = os.getenv("LAKEBASE_INSTANCE", "northbeam-enrichment")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID")
SEGMENTS = ["HIGH PROTEIN", "ENERGY", "NOURISH", "DIET", "TREAT", "NOT A SNACK BAR"]


# ---------------------------------------------------------------------------
# Lakebase connection (OAuth token refreshed before it expires)
# ---------------------------------------------------------------------------
@st.cache_resource
def _token_state():
    return {"token": None, "ts": 0.0}


def get_conn():
    state = _token_state()
    if not state["token"] or time.time() - state["ts"] > 45 * 60:
        cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[INSTANCE])
        state.update(token=cred.token, ts=time.time())
    return psycopg.connect(
        host=os.environ["PGHOST"], port=os.getenv("PGPORT", "5432"), dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"], password=state["token"], sslmode=os.getenv("PGSSLMODE", "require"))


def query(sql, params=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def execute(sql, params):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)


def current_user():
    headers = st.context.headers if hasattr(st, "context") else {}
    return headers.get("X-Forwarded-Email") or headers.get("X-Forwarded-Preferred-Username") or "unknown@northbeam.example"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("🍫 Northbeam · Snack Bar Product Enrichment")
st.caption("Calories, protein and segment for every new retailer product, with evidence, confidence and analyst review.")
market = st.sidebar.selectbox("Market", ["ALL", "ES", "US"])
mfilter, mparams = ("WHERE market = %s", (market,)) if market != "ALL" else ("", ())
tab_overview, tab_review, tab_genie = st.tabs(["Overview", "Review queue", "Ask Genie"])

with tab_overview:
    k = query(f"""
      SELECT count(*) AS products,
             count(*) FILTER (WHERE NOT needs_review OR human_verified) AS enriched,
             count(*) FILTER (WHERE needs_review AND NOT human_verified) AS to_review,
             count(*) FILTER (WHERE human_verified) AS verified,
             round(avg(confidence_score)::numeric, 1) AS avg_conf
      FROM public.gold_product_enrichment {mfilter}""", mparams).iloc[0]
    c = st.columns(4)
    c[0].metric("Products", int(k.products))
    c[1].metric("Enriched (auto + verified)", f"{k.enriched / max(k.products, 1):.0%}")
    c[2].metric("Waiting for review", int(k.to_review))
    c[3].metric("Avg confidence", k.avg_conf)
    left, right = st.columns(2)
    seg = query(f"""SELECT coalesce(segment, 'UNRESOLVED') AS segment, count(*) AS products
                    FROM public.gold_product_enrichment {mfilter} GROUP BY 1 ORDER BY 2 DESC""", mparams)
    left.subheader("Segment mix")
    left.bar_chart(seg.set_index("segment"))
    wk = query(f"""SELECT first_enriched_week AS week, count(*) AS new_products,
                          count(*) FILTER (WHERE NOT needs_review) AS auto_enriched
                   FROM public.gold_product_enrichment {mfilter} GROUP BY 1 ORDER BY 1""", mparams)
    right.subheader("New products per delivery week")
    right.bar_chart(wk.set_index("week"))

with tab_review:
    st.subheader("Products that need an analyst")
    st.caption("Sorted by confidence (lowest first). Approving or correcting sets confidence to 100 and the value is never overwritten by later runs.")
    q = query(f"""
      SELECT g.market, g.item_id, g.descriptor_en, g.brand, g.evidence_tier, g.matched_product_name,
             g.kcal_per_bar, g.protein_g_per_bar, g.segment, g.claimed_ingredient, g.confidence_score, g.explanation
      FROM public.gold_product_enrichment g
      LEFT JOIN (SELECT DISTINCT market, item_id FROM review.review_decisions) d
        ON d.market = g.market AND d.item_id = g.item_id
      WHERE g.needs_review AND NOT g.human_verified AND d.item_id IS NULL
        {"AND g.market = %s" if market != "ALL" else ""}
      ORDER BY g.confidence_score ASC, g.item_id LIMIT 200""", mparams)
    st.write(f"{len(q)} products waiting")
    st.dataframe(q.drop(columns=["explanation"]), use_container_width=True, hide_index=True)
    if len(q):
        pick = st.selectbox("Product to review", q["item_id"] + " · " + q["descriptor_en"].fillna(""))
        row = q[q["item_id"] == pick.split(" · ")[0]].iloc[0]
        st.info(f"**Why the AI is unsure:** {row.explanation}")
        with st.form("decision", clear_on_submit=True):
            action = st.radio("Decision", ["approve", "correct", "reject"], horizontal=True)
            col1, col2, col3 = st.columns(3)
            new_seg = col1.selectbox("Segment", SEGMENTS, index=SEGMENTS.index(row.segment) if row.segment in SEGMENTS else 0)
            new_protein = col2.number_input("Protein g per bar", value=float(row.protein_g_per_bar or 0), step=0.1)
            new_kcal = col3.number_input("kcal per bar", value=float(row.kcal_per_bar or 0), step=1.0)
            comment = st.text_input("Comment (e.g. a definition issue for the category team)")
            if st.form_submit_button("Save decision"):
                user = current_user()
                if action == "correct":
                    changes = [("segment", row.segment, new_seg), ("protein_g_per_bar", row.protein_g_per_bar, new_protein),
                               ("kcal_per_bar", row.kcal_per_bar, new_kcal)]
                    changes = [c for c in changes if str(c[1]) != str(c[2])] or [("segment", row.segment, new_seg)]
                else:
                    changes = [("segment", row.segment, row.segment)]
                none_if_nan = lambda v: None if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
                for field, old, new in changes:
                    execute("""INSERT INTO review.review_decisions
                               (market, item_id, action, field, ai_value, corrected_value, comment, reviewer_email)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (row.market, row.item_id, action, field, none_if_nan(old),
                             None if action == "reject" else str(new), comment or None, user))
                st.success(f"Saved: {action} for {row.item_id}. It will be applied to the gold table on the next run.")
                st.rerun()
    st.divider()
    st.subheader("Recent decisions")
    st.dataframe(query("""SELECT market, item_id, action, field, ai_value, corrected_value, comment, reviewer_email, reviewed_at, applied
                          FROM review.review_decisions ORDER BY reviewed_at DESC LIMIT 20"""),
                 use_container_width=True, hide_index=True)

with tab_genie:
    st.subheader("Ask about the product master")
    st.caption("Powered by a Genie space over the governed Unity Catalog tables and the KPI metric view.")
    examples = ["What is the high-protein share of snack bars in Spain vs the US?",
                "How many products are waiting for analyst review, by market?",
                "Which brands have the most protein per bar on average?"]
    question = st.text_input("Question", value=st.session_state.get("q", examples[0]))
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex{i}"):
            st.session_state["q"] = ex
            st.rerun()
    if st.button("Ask Genie", type="primary") and GENIE_SPACE_ID:
        with st.spinner("Genie is thinking..."):
            msg = w.genie.start_conversation_and_wait(GENIE_SPACE_ID, question)
        for a in msg.attachments or []:
            if a.text:
                st.markdown(a.text.content)
            if a.query:
                with st.expander("SQL"):
                    st.code(a.query.query, language="sql")
                res = w.genie.get_message_attachment_query_result(GENIE_SPACE_ID, msg.conversation_id, msg.id, a.attachment_id)
                sr = res.statement_response
                if sr and sr.result and sr.result.data_array:
                    st.dataframe(pd.DataFrame(sr.result.data_array, columns=[c.name for c in sr.manifest.schema.columns]),
                                 hide_index=True)
