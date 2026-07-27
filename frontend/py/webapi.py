"""Glue module loaded into Pyodide by the frontend. Not part of the compiler
itself -- runs the real pipeline (tokenize -> parse -> generate_ir ->
generate_assembly) stage by stage and serializes each stage's result (or
the exception that stopped it) to JSON for app.js to render.
"""

import json
from dataclasses import fields
from typing import Any

import astree as ast
from assembly_generator import generate_assembly
from ir_generator import GLOBAL_SYMTAB, generate_ir
from parser import parse
from tokenizer import Location, Token, tokenize


def _loc_to_dict(loc: Location) -> dict[str, int]:
    return {"line": loc.line, "column": loc.column}


def _token_to_dict(token: Token) -> dict[str, Any]:
    return {
        "text": token.text,
        "type": token.type,
        "location": _loc_to_dict(token.location),
    }


def _value_to_json(value: Any) -> Any:
    if isinstance(value, ast.Expression):
        return _ast_to_dict(value)
    if isinstance(value, list):
        return [_value_to_json(v) for v in value]
    if isinstance(value, Location):
        return _loc_to_dict(value)
    if isinstance(value, ast.Type):
        return repr(value)
    return value


def _ast_to_dict(node: ast.Expression) -> dict[str, Any]:
    result: dict[str, Any] = {
        "node": type(node).__name__,
        "location": _loc_to_dict(node.location),
    }
    for f in fields(node):
        if f.name == "location":
            continue
        result[f.name] = _value_to_json(getattr(node, f.name))
    return result


def compile_all(source: str) -> str:
    """Runs the full pipeline and returns a JSON string describing each
    stage. A stage that raises stops the pipeline -- later stages are
    omitted entirely rather than showing stale or partial data."""
    stages: dict[str, Any] = {}
    result = {"stages": stages}

    try:
        tokens = tokenize(source)
    except Exception as e:
        stages["tokens"] = {"ok": False, "error": str(e)}
        return json.dumps(result)
    stages["tokens"] = {"ok": True, "data": [
        _token_to_dict(t) for t in tokens]}

    try:
        tree = parse(tokens)
    except Exception as e:
        stages["ast"] = {"ok": False, "error": str(e)}
        return json.dumps(result)
    stages["ast"] = {"ok": True, "data": _ast_to_dict(tree)}

    try:
        instructions = generate_ir(GLOBAL_SYMTAB, tree)
    except Exception as e:
        stages["ir"] = {"ok": False, "error": str(e)}
        return json.dumps(result)
    stages["ir"] = {"ok": True, "data": [str(i) for i in instructions]}

    try:
        assembly = generate_assembly(instructions)
    except Exception as e:
        stages["assembly"] = {"ok": False, "error": str(e)}
        return json.dumps(result)
    stages["assembly"] = {"ok": True, "data": assembly}

    return json.dumps(result)
