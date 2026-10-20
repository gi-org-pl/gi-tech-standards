#!/usr/bin/env python3
"""The contracts of the front-end pre-check, in one place.

- OUTCOMES: the one set of outcome states, with whether the required check
  passes and which label is set. Every component takes them from here.
- validate(): a small JSON-schema validator for the subset the pre-check's
  schemas use (type, properties, required, additionalProperties, enum, items,
  minItems, maxItems, maxLength, minimum, maximum), so that the collected
  scope and the reviewer's output are checked at each boundary without
  installing a package on the runner.

Command line, for report.sh:
  contracts.py passes OUTCOME   exit 0 if the check passes, 1 otherwise
  contracts.py label OUTCOME    print the label ("" for none)
  contracts.py labels           print every label, one per line
  contracts.py validate SCHEMA FILE   exit 0 if FILE matches SCHEMA
"""

import json
import sys

# Outcome -> (does frontend-pre-check / review pass, label)
OUTCOMES = {
    "clean": (True, "pre-check: clean"),          # no findings, full deterministic coverage
    "advisory": (True, "pre-check: advisory"),    # only non-blocking findings, full coverage
    "queued": (True, ""),                         # merge queue entry whose PRs passed on their heads
    "changes": (False, "pre-check: changes"),     # at least one blocking finding
    "human": (False, "pre-check: human review"),  # a rule says a person must judge it (incl. withheld output)
    "invalid": (False, ""),                       # no valid result: the run failed, the output was malformed, or the input was refused
    "skipped": (False, ""),                       # not pre-checked: fork, draft, bot, no write access, no secret, run limit
}

LABEL_COLOURS = {
    "pre-check: clean": ("0e8a16", "AI pre-check reported no findings; not an approval"),
    "pre-check: advisory": ("c2e0c6", "AI pre-check passed with advisory findings; not an approval"),
    "pre-check: changes": ("d93f0b", "AI pre-check found something to fix"),
    "pre-check: human review": ("fbca04", "AI pre-check cannot judge this pull request; a person reviews it"),
}

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _is_type(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def errors(value, schema, path="$"):
    """Returns a list of violations of SCHEMA by VALUE (empty when valid)."""
    found = []
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, n) for n in names):
            return ["{}: expected {}".format(path, "/".join(names))]
    if "enum" in schema and value not in schema["enum"]:
        found.append("{}: not one of {}".format(path, schema["enum"]))
    if isinstance(value, str):
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            found.append("{}: longer than {}".format(path, schema["maxLength"]))
    if _is_type(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            found.append("{}: below {}".format(path, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            found.append("{}: above {}".format(path, schema["maximum"]))
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            found.append("{}: more than {} items".format(path, schema["maxItems"]))
        if "minItems" in schema and len(value) < schema["minItems"]:
            found.append("{}: fewer than {} items".format(path, schema["minItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                found += errors(item, schema["items"], "{}[{}]".format(path, i))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                found.append("{}: missing {}".format(path, key))
        for key, item in value.items():
            if key in props:
                found += errors(item, props[key], "{}.{}".format(path, key))
            elif schema.get("additionalProperties") is False:
                found.append("{}: unexpected {}".format(path, key))
            elif isinstance(schema.get("additionalProperties"), dict):
                found += errors(item, schema["additionalProperties"], "{}.{}".format(path, key))
    return found


def validate(value, schema):
    return not errors(value, schema)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    if command == "passes":
        return 0 if OUTCOMES.get(argv[2], (False, ""))[0] else 1
    if command == "label":
        print(OUTCOMES.get(argv[2], (False, ""))[1])
        return 0
    if command == "labels":
        for label in LABEL_COLOURS:
            colour, description = LABEL_COLOURS[label]
            print("{}\t{}\t{}".format(label, colour, description))
        return 0
    if command == "validate":
        try:
            problems = errors(load(argv[3]), load(argv[2]))
        except (OSError, ValueError) as error:
            problems = [str(error)]
        for problem in problems[:20]:
            print(problem, file=sys.stderr)
        return 0 if not problems else 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
