#!/usr/bin/env python3
"""Compare effective user/company navigation; a larger count cannot mask loss."""
import argparse
import json
from pathlib import Path


def compare(before, after):
    errors = []
    if before.get("status") != "passed" or after.get("status") != "passed":
        errors.append("incomplete snapshot")
    if before.get("database") != after.get("database"):
        errors.append("database identity mismatch")
    def principals(snapshot):
        out = {}
        for row in snapshot.get("principals", []):
            key = (row["user_id"], row["company_id"])
            if key in out:
                errors.append(f"duplicate principal {key}")
            out[key] = row
        return out
    old, new = principals(before), principals(after)
    if not old:
        errors.append("empty baseline principal set")
    details = []
    for key, previous in old.items():
        current = new.get(key)
        if current is None:
            errors.append(f"missing principal {key}")
            continue
        if previous.get("groups") != current.get("groups"):
            errors.append(f"permission context changed {key}")
        def nodes(row):
            result = {}
            for node in row["nodes"]:
                identity = str(node.get("key") or "")
                if not identity or identity in result:
                    errors.append(f"missing/duplicate node identity {key}: {identity}")
                result[identity] = node
            return result
        a, b = nodes(previous), nodes(current)
        missing = sorted(a.keys() - b.keys())
        changed = [identity for identity in a.keys() & b.keys() if a[identity] != b[identity]]
        if missing or changed:
            errors.append(f"navigation loss/drift {key}: missing={missing} changed={changed}")
        if list(a) != [identity for identity in b if identity in a]:
            errors.append(f"existing menu order changed {key}")
        details.append({"user_id":key[0],"company_id":key[1],"before":len(a),"after":len(b),"added":sorted(b.keys()-a.keys()),"missing":missing,"changed":changed})
    return {"status":"passed" if not errors else "failed","errors":errors,"principals":details}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compare(json.loads(Path(args.before).read_text()),json.loads(Path(args.after).read_text()))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({"status":result["status"],"principals":len(result["principals"]),"errors":result["errors"]},ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
