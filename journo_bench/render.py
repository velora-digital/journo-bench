"""Render report/report.md to a PDF.

Keeps report.md as the single source of truth: this fills the chart slots with
the actual figures, marks any still-unfilled `[[DATA]]` slot as a visible pending
note (rather than leaking raw tag text into the PDF), writes a built copy, and
runs Pandoc with the Typst engine.

    uv run -m evals_public.journo_research.render

Requires pandoc and typst on PATH:  brew install pandoc typst
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "report" / "report.md"
BUILT = HERE / "report" / "report.built.md"
PDF = HERE / "report" / "report.pdf"
CHARTS = HERE / "charts"


def _fill(md: str) -> str:
    """Swap chart slots for image embeds; turn other [[DATA]] slots into a note."""

    def chart(m: re.Match) -> str:
        name = Path(m.group(1).strip()).name
        for ext in ("svg", "png"):
            p = CHARTS / f"{name}.{ext}"
            if p.exists():
                return f"![]({p}){{width=85%}}"
        return f"*[missing chart: {name}]*"

    md = re.sub(r"\[\[DATA:\s*charts/([^\]]+)\]\]", chart, md)
    md = re.sub(r"\[\[DATA:\s*([^\]]+)\]\]", lambda m: f"*[pending: {m.group(1).strip()}]*", md)
    return md


def main() -> None:
    if not shutil.which("pandoc") or not shutil.which("typst"):
        sys.exit("pandoc and typst required. Install with: brew install pandoc typst")
    BUILT.write_text(_fill(SRC.read_text()))
    cmd = [
        "pandoc",
        str(BUILT),
        "-o",
        str(PDF),
        "--pdf-engine=typst",
        "--toc",
    ]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"wrote {PDF}")


if __name__ == "__main__":
    main()
