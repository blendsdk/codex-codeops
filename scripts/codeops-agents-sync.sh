#!/usr/bin/env bash
#
# codeops-agents-sync.sh — materialize per-repo agent effort overrides without forking prompts.
#
# CodeOps Skills Version: 3.12.0
#
# A subagent's MODEL can be redirected at dispatch time, so an `agent_models` entry naming only a
# model needs no file on disk. A subagent's EFFORT cannot: Claude Code reads it from the agent's
# own frontmatter and offers no dispatch parameter, env var, or settings key. Until it does, the
# only way to honor an effort override is to have a file in the repo's `.claude/agents/`.
#
# Hand-copying the plugin's agent to change one frontmatter line is what this script exists to
# replace. A hand copy is a silent, permanent fork: the plugin ships an improved prompt and the
# repo keeps the old one forever, with nothing to notice it by. So this engine GENERATES those
# files instead — body copied byte-for-byte from the plugin, only frontmatter rewritten, and a
# `CODEOPS-GENERATED` marker carrying the plugin version that produced it. A stale stamp is
# therefore detectable, and regeneration is a no-op when nothing changed.
#
# Ownership is explicit and one-directional: this engine owns files carrying its marker and
# nothing else. A hand-authored agent of the same name is reported and left completely alone —
# deliberately forking a prompt stays legal, it just stops being the only option.
#
# Reads, from the repo it is run in:
#   CLAUDE.md → the `<!-- CODEOPS-QUALITY -->` block → `agent_models`
# Value forms (see _shared/quality-profile.md):
#   name: model                      → model only; applied at dispatch, no file
#   name: {model: M, effort: E}      → file, both fields rewritten
#   name: {effort: E}                → file; model stays the plugin's pin
#
# Usage:
#   codeops-agents-sync.sh            # generate / update / prune in place
#   codeops-agents-sync.sh --check    # report drift, change nothing; exit 1 on drift
#   codeops-agents-sync.sh --dry-run  # print the would-be work, change nothing
# Env:
#   CODEOPS_PLUGIN_ROOT               # plugin root override (default: this script's parent)
# Exit: 0 = in sync / updated / only warnings; 1 = drift found (--check) or write failure;
#       2 = bad usage; 3 = python3 unavailable.
#
# It never executes repo data — the profile block is parsed as text, never sourced or evaluated.

set -uo pipefail

MODE="write"
for arg in "$@"; do
  case "$arg" in
    --check)   MODE="check" ;;
    --dry-run) MODE="dry" ;;
    -h|--help) grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || {
  printf 'ERROR: python3 is required for agent frontmatter parsing.\n' >&2
  exit 3
}

# Resolve the plugin root through any symlink chain the dev installer may have created.
resolve_self() {
  local src="${BASH_SOURCE[0]}" dir
  while [[ -L "$src" ]]; do
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd -P "$(dirname "$src")" && pwd
}
PLUGIN_ROOT="${CODEOPS_PLUGIN_ROOT:-$(cd "$(resolve_self)/.." && pwd)}"

if [[ ! -d "$PLUGIN_ROOT/agents" ]]; then
  printf 'ERROR: no agents/ directory under plugin root %s\n' "$PLUGIN_ROOT" >&2
  exit 1
fi

MODE="$MODE" PLUGIN_ROOT="$PLUGIN_ROOT" python3 - <<'PY'
import json, os, re, sys

mode = os.environ["MODE"]                # write | check | dry
plugin_root = os.environ["PLUGIN_ROOT"]

VALID_EFFORT = ("low", "medium", "high", "xhigh", "max")
VALID_MODEL = ("sonnet", "opus", "haiku", "fable", "inherit")
MARKER = "CODEOPS-GENERATED"
AGENTS_DIR = os.path.join(".claude", "agents")

changed = False        # any write performed (write mode)
drift = False          # any divergence found (check mode)
warned = False


def say(tag, msg):
    print(f"  {tag:<9} {msg}")


def plugin_version():
    path = os.path.join(plugin_root, ".claude-plugin", "plugin.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return str(json.load(fh).get("version") or "unknown")
    except (OSError, ValueError):
        return "unknown"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def split_frontmatter(text):
    """Return (frontmatter_lines, body_text). body_text keeps its leading newline."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def split_top_level(raw):
    """Split a one-line inline map's contents on commas at brace depth 0."""
    out, depth, cur = [], 0, []
    for ch in raw:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return [p.strip() for p in out if p.strip()]


def parse_overrides(claude_md):
    """Parse agent_models out of the quality block. Lenient: bad entries warn and are dropped."""
    global warned
    if not os.path.isfile(claude_md):
        return None
    text = read(claude_md)
    block = re.search(
        r"<!--\s*CODEOPS-QUALITY:START\s*-->(.*?)<!--\s*CODEOPS-QUALITY:END\s*-->",
        text, re.S)
    if not block:
        return None
    line = re.search(r"^agent_models:\s*(.*)$", block.group(1), re.M)
    if not line:
        return {}
    raw = line.group(1).strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
    result = {}
    for entry in split_top_level(raw):
        if ":" not in entry:
            say("WARN", f"unparseable agent_models entry, ignored: {entry}")
            warned = True
            continue
        name, value = entry.split(":", 1)
        name, value = name.strip(), value.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
            say("WARN", f"invalid agent name, ignored: {name!r}")
            warned = True
            continue
        spec = {}
        if value.startswith("{"):
            for pair in split_top_level(value.strip("{}")):
                if ":" not in pair:
                    say("WARN", f"{name}: unparseable override {pair!r}, ignored")
                    warned = True
                    continue
                k, v = (p.strip() for p in pair.split(":", 1))
                if k in ("model", "effort"):
                    spec[k] = v
                else:
                    say("WARN", f"{name}: unknown override key {k!r}, ignored")
                    warned = True
        else:
            spec["model"] = value
        result[name] = spec
    return result


def validate(name, spec):
    """Drop unusable values with a warning; return the surviving spec."""
    global warned
    clean = {}
    model = spec.get("model")
    if model is not None:
        if model in VALID_MODEL:
            clean["model"] = model
        else:
            say("WARN", f"{name}: model {model!r} not in {'|'.join(VALID_MODEL)}, ignored")
            warned = True
    effort = spec.get("effort")
    if effort is not None:
        if effort in VALID_EFFORT:
            clean["effort"] = effort
        else:
            say("WARN", f"{name}: effort {effort!r} not in {'|'.join(VALID_EFFORT)}, ignored")
            warned = True
    return clean


def render(name, spec, version):
    """Build the generated agent: plugin frontmatter with model/effort rewritten, body verbatim."""
    source = os.path.join(plugin_root, "agents", f"{name}.md")
    fm, body = split_frontmatter(read(source))
    if fm is None:
        return None
    out, seen = [], set()
    for line in fm:
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in ("model", "effort") and key in spec:
            out.append(f"{key}: {spec[key]}")
            seen.add(key)
        else:
            if key in ("model", "effort"):
                seen.add(key)
            out.append(line)
    for key in ("model", "effort"):
        if key in spec and key not in seen:
            out.append(f"{key}: {spec[key]}")
    marker = (f"<!-- {MARKER} agent={name} version={version} source=agents/{name}.md — "
              f"generated by CodeOps; regenerate with /setup_routing, do not hand-edit -->")
    return "---\n" + "\n".join(out) + "\n---\n" + marker + "\n" + body


def is_generated(path):
    try:
        return MARKER in read(path)
    except OSError:
        return False


version = plugin_version()
overrides = parse_overrides("CLAUDE.md")

if overrides is None:
    print("No CodeOps quality-profile block in CLAUDE.md — nothing to sync.")
    sys.exit(0)

wanted = {}
for name, spec in overrides.items():
    spec = validate(name, spec)
    if "effort" not in spec:
        continue  # model-only overrides are applied at dispatch time; no file needed
    if not os.path.isfile(os.path.join(plugin_root, "agents", f"{name}.md")):
        say("WARN", f"{name}: no such plugin agent, ignored")
        warned = True
        continue
    wanted[name] = spec

for name in sorted(wanted):
    target = os.path.join(AGENTS_DIR, f"{name}.md")
    desired = render(name, wanted[name], version)
    if desired is None:
        say("WARN", f"{name}: plugin agent has no frontmatter, ignored")
        warned = True
        continue
    if os.path.isfile(target):
        if not is_generated(target):
            say("SKIPPED", f"{target} is hand-authored — left untouched")
            continue
        if read(target) == desired:
            say("UNCHANGED", target)
            continue
        verb = "UPDATED"
    else:
        verb = "CREATED"
    if mode == "check":
        say("DRIFT", f"{target} would be {verb.lower()}")
        drift = True
        continue
    if mode == "dry":
        say(verb, f"{target} (dry run)")
        continue
    os.makedirs(AGENTS_DIR, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(desired)
    say(verb, target)
    changed = True

# Prune generated files whose override was withdrawn — otherwise removing an override from the
# profile would silently leave the old pin in force.
if os.path.isdir(AGENTS_DIR):
    for fname in sorted(os.listdir(AGENTS_DIR)):
        if not fname.endswith(".md"):
            continue
        name = fname[:-3]
        if name in wanted:
            continue
        path = os.path.join(AGENTS_DIR, fname)
        if not is_generated(path):
            continue
        if mode == "check":
            say("DRIFT", f"{path} would be pruned (no effort override)")
            drift = True
            continue
        if mode == "dry":
            say("PRUNED", f"{path} (dry run)")
            continue
        try:
            os.remove(path)
        except OSError as exc:
            say("ERROR", f"cannot prune {path}: {exc}")
            sys.exit(1)
        say("PRUNED", path)
        changed = True

if mode == "check":
    print("Drift found." if drift else "Generated agents are in sync.")
    sys.exit(1 if drift else 0)
if mode == "dry":
    print("Dry run — nothing written.")
    sys.exit(0)
print("Generated agents updated." if changed else "Generated agents already in sync.")
sys.exit(0)
PY
