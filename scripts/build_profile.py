"""Build README, individual SVG modules, responsive rows and a local preview.

Usage: python scripts/build_profile.py [--check]
Python 3.8+, standard library only. No network calls or secret tokens.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from profile_ui import RENDERERS, avatar, document, esc, hero, module

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc


def valid_url(url):
    if not url:
        return True
    parsed = urlparse(url)
    return not any(c.isspace() or c in '<>"' for c in url) and (
        (parsed.scheme == "https" and bool(parsed.netloc)) or
        (parsed.scheme == "mailto" and bool(parsed.path) and "@" in parsed.path))


def validate_strings(value):
    if isinstance(value, str):
        if any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError("Text contains an XML-incompatible control character")
    elif isinstance(value, dict):
        for key, child in value.items():
            if key == "url" and (not isinstance(child, str) or not valid_url(child)):
                raise ValueError(f"Use a valid https:// or mailto: URL: {child!r}")
            if key == "accent" and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(child)):
                raise ValueError("Accent must be a six-digit hex color")
            validate_strings(child)
    elif isinstance(value, list):
        for child in value:
            validate_strings(child)


def require_text(record, fields, context):
    if not isinstance(record, dict):
        raise ValueError(f"{context}: expected an object")
    for key in fields:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"{context}: {key} must be nonempty text")


def load(root=ROOT):
    profile = read_json(root / "profile/profile.json")
    require_text(profile, ["username", "name", "title", "subtitle", "bio", "motto", "status"], "profile")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", profile["username"]):
        raise ValueError("Invalid GitHub username")
    for key in ("navy", "ink", "muted", "gold", "border", "paper", "paper_deep"):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", profile.get("theme", {}).get(key, "")):
            raise ValueError(f"theme.{key} must be a six-digit hex color")
    layout = read_json(root / "profile/layout.json")
    rows = layout.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("layout.rows must be a nonempty list")
    modules, seen, active = {}, set(), []
    fields = {"facts": ["label", "value"], "skills": ["label"],
              "timeline": ["date", "title", "body"], "cards": ["title", "body"],
              "projects": ["title", "body", "contribution"],
              "games": ["title", "server", "uid", "status"], "links": ["label"]}
    for row in rows:
        if not isinstance(row, list) or not 1 <= len(row) <= 2:
            raise ValueError("Each layout row must contain one or two module IDs")
        enabled = []
        for module_id in row:
            if not isinstance(module_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", module_id):
                raise ValueError(f"Invalid module ID: {module_id!r}")
            if module_id in seen:
                raise ValueError(f"Duplicate module ID: {module_id}")
            seen.add(module_id)
            data = read_json(root / "profile/modules" / f"{module_id}.json")
            if not isinstance(data.get("enabled", True), bool):
                raise ValueError(f"{module_id}.enabled must be true or false")
            if not data.get("enabled", True):
                continue
            require_text(data, ["type", "title"], module_id)
            kind = data["type"]
            if kind not in RENDERERS:
                raise ValueError(f"Unknown module type: {kind}")
            items = data.get("groups" if kind == "skills" else "items")
            if not isinstance(items, list) or not items:
                raise ValueError(f"{module_id}: provide at least one item, or set enabled=false")
            if type(data.get("columns", 2)) is not int or not 1 <= data.get("columns", 2) <= 3:
                raise ValueError(f"{module_id}.columns must be 1, 2, or 3")
            for item in items:
                require_text(item, fields[kind], module_id)
                if kind in ("skills", "projects"):
                    tags = item.get("tags")
                    if not isinstance(tags, list) or not all(isinstance(t, str) and t.strip() for t in tags):
                        raise ValueError(f"{module_id}: tags must be a list of nonempty strings")
            validate_strings(data)
            modules[module_id] = data
            enabled.append(module_id)
        if enabled:
            active.append(enabled)
    validate_strings(profile)
    return profile, modules, active


def text_lines(data):
    kind = data["type"]
    for item in data.get("groups", data.get("items", [])):
        if kind == "facts":
            yield f'{item["label"]}：{item["value"]}'
        elif kind == "skills":
            yield f'{item["label"]}：'+" / ".join(item["tags"])
        elif kind == "timeline":
            yield f'{item["date"]} · {item["title"]} — {item["body"]}'
        elif kind == "games":
            yield f'{item["title"]}｜服务器：{item["server"]}｜UID：{item["uid"]}｜游玩状态：{item["status"]}'
        elif kind == "links":
            yield f'{item["label"]}：{item.get("url") or "待填写"}'
        else:
            line = f'{item["title"]}：{item["body"]}'
            if kind == "projects":
                line += f'；我的贡献：{item["contribution"]}；技术栈：'+" / ".join(item["tags"])
            yield line
    if data.get("note"):
        yield data["note"]


def picture(name, alt, prefix=""):
    return (f'<picture>\n'
            f'  <source media="(max-width: 600px)" srcset="{prefix}assets/generated/{name}-mobile.svg">\n'
            f'  <img src="{prefix}assets/generated/{name}.svg" width="100%" alt="{esc(alt)}">\n'
            '</picture>')


def link_list(ids, modules):
    items = []
    for module_id in ids:
        data = modules[module_id]
        for item in data.get("items", []):
            if item.get("url"):
                label = item.get("label", item.get("title", "Link"))
                items.append(f'<a href="{esc(item["url"])}">{esc(label)} ↗</a>')
    return '<p align="center">'+" &nbsp; · &nbsp; ".join(items)+"</p>" if items else ""


def build(root=ROOT):
    profile, modules, rows = load(root)
    theme = profile["theme"]
    outputs = {}
    sections = []
    for suffix, width in (("", 1000), ("-mobile", 520)):
        fragment, height = hero(profile, width)
        outputs[f"assets/generated/hero{suffix}.svg"] = document(fragment, width, height, profile["title"], theme)
        for index, ids in enumerate(rows, 1):
            pieces, offset, row_height = [], 0, 0
            col_width = (width-16*(len(ids)-1))/len(ids) if not suffix else width
            min_height = max(module(modules[i], col_width, theme)[1] for i in ids) if not suffix else 0
            for module_id in ids:
                fragment, height = module(modules[module_id], col_width, theme, min_height)
                outputs[f"assets/generated/module-{module_id}{suffix}.svg"] = document(fragment, col_width, height, modules[module_id]["title"], theme)
                x, y = (offset, 0) if not suffix else (0, offset)
                pieces.append(f'<g transform="translate({x},{y})">{fragment}</g>')
                offset += (col_width if not suffix else height)+16
                row_height = max(row_height, height) if not suffix else offset-16
            outputs[f"assets/generated/row-{index:02d}{suffix}.svg"] = document("".join(pieces), width, row_height, ' / '.join(modules[i]["title"] for i in ids), theme)
    outputs["assets/avatar.svg"] = avatar(theme)
    for index, ids in enumerate(rows, 1):
        title = " · ".join(modules[i]["title"] for i in ids)
        alt = title+"。"+"；".join(line for i in ids for line in text_lines(modules[i]))
        sections.append(picture(f"row-{index:02d}", alt))
        links_html = link_list(ids, modules)
        if links_html:
            sections.append(links_html)
    transcript = [f'<p>{esc(profile["name"])} · @{esc(profile["username"])}<br>{esc(profile["bio"])}</p>']
    for ids in rows:
        for module_id in ids:
            data = modules[module_id]
            transcript.append(f'<h3>{esc(data["title"])}</h3>\n<ul>')
            transcript.extend(f'<li>{esc(line)}</li>' for line in text_lines(data))
            transcript.append('</ul>')
    transcript.append(f'<p>{esc(profile["status"])}</p>')
    details = '<details>\n<summary>文字版档案 · 复制 UID / 查看全部信息</summary>\n\n'+"\n".join(transcript)+'\n\n</details>'
    body = picture("hero", f'{profile["name"]}的{profile["title"]}。{profile["bio"]}。{profile["motto"]}')+'\n\n'+"\n\n".join(sections)+f'\n\n<p align="center">✦ {esc(profile["status"])} ✦</p>\n\n'+details+'\n'
    outputs["README.md"] = '<!-- Generated by scripts/build_profile.py. Edit profile/*.json and profile/modules/*.json instead. -->\n\n'+body
    preview_body = body.replace('src="assets/', 'src="../assets/').replace('srcset="assets/', 'srcset="../assets/')
    preview_template = (root / "templates/preview.html").read_text(encoding="utf-8")
    outputs["preview/index.html"] = preview_template.replace("{{PROFILE}}", preview_body).replace("{{NAME}}", esc(profile["name"])).replace("{{USERNAME}}", esc(profile["username"])).replace("{{BIO}}", esc(profile["bio"]))
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated files are outdated")
    args = parser.parse_args()
    try:
        outputs = build()
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    manifest = ROOT / "assets/generated/manifest.json"
    old = read_json(manifest) if manifest.exists() else []
    outputs["assets/generated/manifest.json"] = json.dumps(sorted(outputs), indent=2)+"\n"
    stale = [name for name in old if name not in outputs and name.startswith("assets/generated/") and Path(name).name == name.split("/")[-1] 
             and (ROOT/name).resolve().parent == (ROOT/"assets/generated").resolve()]
    changes = [name for name, text in outputs.items() if not (ROOT/name).exists() or (ROOT/name).read_text(encoding="utf-8") != text]
    if args.check:
        if changes or stale:
            print("Generated files are out of date:\n"+"\n".join(changes+stale))
            return 1
        print(f"OK: {len(outputs)} generated files match configuration.")
        return 0
    for name, text in outputs.items():
        path = ROOT/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    for name in stale:
        (ROOT/name).unlink(missing_ok=True)
    print(f"Built {len(outputs)} files. Preview: {ROOT / 'preview/index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
