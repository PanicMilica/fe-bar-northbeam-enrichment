"""Export executed job runs as readable text (code + outputs) into evidence/.

The FE Bar evaluator reads text only, so each notebook task of a job run is
exported (jobs/runs/export), its embedded notebook model is decoded, and every
cell is written to Markdown with its real output: printed text, tables and errors.

Usage: python scripts/export_run_evidence.py <profile> <job_run_id> <label>
"""
import base64, html, json, re, subprocess, sys, urllib.parse
from pathlib import Path

PROFILE, RUN_ID, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
OUT = Path(__file__).resolve().parents[1] / "evidence" / "job_runs" / LABEL
OUT.mkdir(parents=True, exist_ok=True)


def cli(*args):
    r = subprocess.run(["databricks", *args, "-p", PROFILE, "-o", "json"], capture_output=True, text=True)
    return json.loads(r.stdout)


def notebook_model(page):
    m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", page)
    if not m:
        return None
    raw = base64.b64decode(m.group(1)).decode("utf-8")
    return json.loads(urllib.parse.unquote(raw))


def render_result(res):
    if not res:
        return []
    t, data = res.get("type"), res.get("data")
    if t == "listResults" and isinstance(data, list):
        return [line for sub in data for line in render_result(sub)]
    if t == "ansi" and isinstance(data, str):
        text = re.sub(r"\x1b\[[0-9;]*m", "", data).rstrip()
        return ["```text", text[:6000], "```"] if text else []
    if t == "mimeBundle" and isinstance(data, dict):
        text = data.get("text/plain", "")
        return [] if not text or text.startswith("DataFrame[") else ["```text", text[:3000], "```"]
    if t == "raw" and isinstance(data, str) and data.strip():
        return ["```text", "notebook exit value: " + data[:3000], "```"]
    if t in ("text", "listResults") and isinstance(data, str) and data.strip():
        return ["```text", data.rstrip()[:6000], "```"]
    if t == "table" and isinstance(data, list):
        cols = [c.get("name") for c in res.get("schema", [])]
        rows = data[:25]
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join("" if v is None else str(v).replace("|", "/").replace("\n", " ")[:120] for v in r) + " |"
                  for r in rows]
        if len(data) > 25:
            lines.append(f"_... {len(data) - 25} more rows_")
        return lines
    if t == "html" and isinstance(data, str):
        text = re.sub(r"<[^>]+>", " ", data)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return ["```text", text[:3000], "```"] if text else []
    if t == "error":
        return ["```text", "ERROR: " + str(res.get("summary") or data)[:3000], "```"]
    return []


run = cli("jobs", "get-run", RUN_ID)
index = [f"# Job run {RUN_ID} ({LABEL})", "",
         f"Job: `{run.get('run_name')}` · result: **{run.get('state', {}).get('result_state')}** · "
         f"run page: {run.get('run_page_url')}", "", "| task | result | duration (s) | evidence |", "|---|---|---|---|"]
for task in sorted(run.get("tasks", []), key=lambda t: t.get("start_time", 0)):
    key, state = task["task_key"], task.get("state", {}).get("result_state")
    dur = round((task.get("end_time", 0) - task.get("start_time", 0)) / 1000)
    if "pipeline_task" in task:
        index.append(f"| {key} | {state} | {dur} | Lakeflow pipeline update (see [../../lakeflow_pipeline.md](../../lakeflow_pipeline.md)) |")
        continue
    exp = cli("jobs", "export-run", str(task["run_id"]), "--views-to-export", "CODE")
    lines = [f"# {key} · task run {task['run_id']} · {state}", ""]
    for view in exp.get("views", []):
        model = notebook_model(view.get("content", ""))
        if not model:
            continue
        lines.append(f"Notebook: `{model.get('name')}` (language: {model.get('language')})")
        for cmd in model.get("commands", []):
            src = (cmd.get("command") or "").rstrip()
            if not src:
                continue
            lang = "sql" if model.get("language") == "sql" and not src.startswith("%") else "python"
            if src.startswith("%md"):
                lines += ["", re.sub(r"^%md\s*", "", src), ""]
                continue
            lines += ["", f"```{lang}", src[:5000], "```"]
            out = render_result(cmd.get("results"))
            if out:
                lines += ["**Output:**", *out]
    (OUT / f"{key}.md").write_text("\n".join(lines))
    index.append(f"| {key} | {state} | {dur} | [{key}.md]({key}.md) |")
    print(f"exported {key}")

out = cli("jobs", "get-run-output", str(next(t["run_id"] for t in run["tasks"] if t["task_key"] == "evaluate"))) \
    if any(t["task_key"] == "evaluate" for t in run.get("tasks", [])) else {}
if out.get("notebook_output", {}).get("result"):
    index += ["", "## Evaluate task output (notebook exit value)", "```json", out["notebook_output"]["result"], "```"]
(OUT / "README.md").write_text("\n".join(index))
print(f"-> {OUT}")
