"""Read a SKILL.md and return its body without YAML frontmatter."""

from __future__ import annotations

from pathlib import Path


def skill_body(skill_dir: Path) -> str:
    """Return the body of `<skill_dir>/SKILL.md` with frontmatter stripped.

    Skills include the base path implicitly. We replace `{skill_path}` placeholder
    if present so each SDK sees an absolute path it can use in Bash commands.
    """
    md = (skill_dir / "SKILL.md").read_text()
    if md.startswith("---"):
        _, _, rest = md.partition("---\n")
        _, _, body = rest.partition("\n---\n")
    else:
        body = md
    return body.replace("{skill_path}", str(skill_dir.resolve()))
