#!/usr/bin/env python3
"""Validate ComfyUI API-format workflow JSON: structure and internal references."""

import json
import sys


def validate_workflow(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        workflow = json.load(f)

    if not isinstance(workflow, dict):
        return [f"Top-level must be a dict (got {type(workflow).__name__})"]

    errors = []
    node_ids = set(workflow.keys())

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            errors.append(f"Node {node_id}: expected dict, got {type(node).__name__}")
            continue
        if "class_type" not in node:
            errors.append(f"Node {node_id}: missing class_type")
        if "inputs" not in node:
            errors.append(f"Node {node_id}: missing inputs")
            continue

        inputs = node["inputs"]
        if not isinstance(inputs, dict):
            errors.append(f"Node {node_id}: inputs must be a dict")
            continue

        for input_name, value in inputs.items():
            if isinstance(value, list) and len(value) == 2:
                ref_id, ref_slot = value
                ref_id_str = str(ref_id)
                if ref_id_str not in node_ids:
                    errors.append(
                        f"Node {node_id}.{input_name}: "
                        f"references node {ref_id_str} which does not exist"
                    )
                if not isinstance(ref_slot, int):
                    errors.append(
                        f"Node {node_id}.{input_name}: "
                        f"output slot must be int (got {type(ref_slot).__name__})"
                    )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <workflow.json> [workflow2.json ...]")
        return 1

    exit_code = 0
    for path in sys.argv[1:]:
        errors = validate_workflow(path)
        if errors:
            print(f"FAIL: {path}")
            for err in errors:
                print(f"  - {err}")
            exit_code = 1
        else:
            print(f"OK: {path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
