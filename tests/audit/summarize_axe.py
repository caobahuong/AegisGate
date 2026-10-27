import json

with open("report/phase-5-audit/t6_ui_audit_evidence.json", encoding="utf-8") as f:
    data = json.load(f)
seen = set()
for item in data["axe_violations_summary"]:
    for v in item["critical_or_serious"]:
        if v["id"] in ("select-name", "aria-valid-attr-value", "label-content-name-mismatch"):
            key = (v["id"], item["screen"])
            if key in seen:
                continue
            seen.add(key)
            print(f"=== Screen: {item['screen']} | Rule: {v['id']} ===")
            for node in v["nodes"][:2]:
                print("  HTML:", node["html"])
                print("  Target:", node["target"])
                print("  Failure:", node["failureSummary"])
