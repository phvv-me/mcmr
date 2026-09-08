from pathlib import Path

import polars as pl

from ...facts import ManuscriptFact
from ...table.session import AnalysisSession
from ..interface import app, console


@app.command
def prose(root: Path = Path()) -> None:
    """Export narrative paragraphs from the shared LaTeX or Typst parser.

    root: manuscript directory; includes follow the document's reading order.
    """
    table = AnalysisSession(root, typed_families=[ManuscriptFact]).table(ManuscriptFact)
    paragraphs = table.records("paragraphs").filter(
        ~pl.col("in_cells") & ~pl.col("in_float") & ~pl.col("in_bibliography")
    )
    sentences = (
        table.records("sentences")
        .join(paragraphs.select("fact_id", "reading_order"), on=["fact_id", "reading_order"])
        .sort("fact_id", "reading_order", "index")
        .group_by("fact_id", "reading_order", maintain_order=True)
        .agg(pl.col("text").str.join(" "))
        .collect()
    )
    for paragraph in sentences.get_column("text"):
        console.print(paragraph, markup=False, highlight=False, soft_wrap=True)
        console.print()
