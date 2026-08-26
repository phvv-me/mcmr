import polars as pl

from ...facts import Fact
from .generic import FactRelations


class ManuscriptRelations[Family: Fact](FactRelations[Family]):
    """Derive reading-order comparisons from normalized manuscript relations."""

    def labelled(self, relation: str, *columns: str) -> pl.LazyFrame:
        """Return one labelled relation beside how often its label is referenced."""
        return (
            self.located(relation, "label", *columns)
            .join(self.reference_counts(), on=["fact_id", "label"], how="left")
            .with_columns(
                pl.col("reference_count").fill_null(0),
                pl.col("first_reference_order").fill_null(0),
            )
        )

    def located(self, relation: str, *columns: str) -> pl.LazyFrame:
        """Return one record relation with the columns every finding needs to place it."""
        return self.records(relation).select(
            "fact_order",
            "fact_id",
            "record_id",
            "reading_order",
            "path",
            pl.col("line").alias("start_line"),
            pl.lit(0, dtype=pl.UInt32).alias("start_column"),
            pl.col("line").alias("end_line"),
            pl.lit(0, dtype=pl.UInt32).alias("end_column"),
            "section_number",
            *columns,
        )

    def reference_counts(self) -> pl.LazyFrame:
        """Return how many cross references name each declared label."""
        references = self.located("references", "target")
        return (
            references.group_by("fact_id", "target", maintain_order=True)
            .agg(
                pl.len().cast(pl.UInt64).alias("reference_count"),
                pl.col("reading_order").min().alias("first_reference_order"),
            )
            .rename({"target": "label"})
        )

    def resolved(self) -> pl.LazyFrame:
        """Return each cross reference beside the target it resolves to.

        A reference naming nothing this manuscript declares keeps a null target order, which is
        what separates a reference into a bibliography or a package from one that points at a
        label the document is missing.
        """
        labels = self.located("labels", "name", "kind").select(
            "fact_id",
            pl.col("name").alias("target"),
            pl.col("reading_order").alias("target_order"),
            pl.col("kind").alias("target_kind"),
            pl.col("path").alias("target_path"),
            pl.col("start_line").alias("target_line"),
        )
        return self.located("references", "target", "command").join(
            labels.unique(subset=["fact_id", "target"], keep="first"),
            on=["fact_id", "target"],
            how="left",
        )
