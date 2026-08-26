"""Every manuscript rule, shown once firing and once staying quiet."""

from mcmr.facts import (
    ManuscriptCitation,
    ManuscriptEntry,
    ManuscriptEvidenceFact,
    ManuscriptFact,
    ManuscriptFloat,
    ManuscriptLabel,
    ManuscriptNotationFact,
    ManuscriptNumber,
    ManuscriptParagraph,
    ManuscriptReference,
    ManuscriptSection,
    ManuscriptSentence,
    ManuscriptStatement,
    ManuscriptSymbol,
    ManuscriptSymbolSite,
    ManuscriptTerm,
)
from mcmr.rules.general.deterministic.manuscript.evidence import (
    measurement_resting_on_an_unpinned_citation,
    prose_number_that_nearly_matches_its_table,
    ratio_published_without_its_parts,
)
from mcmr.rules.general.deterministic.manuscript.notation import (
    notation_entry_absent_from_the_body,
    symbol_introduced_under_two_meanings,
    symbol_missing_from_the_notation_index,
)
from mcmr.rules.general.deterministic.manuscript.order import (
    forward_reference_to_unread_material,
    symbol_used_before_it_is_introduced,
    term_used_before_it_is_marked,
)
from mcmr.rules.general.deterministic.manuscript.prose import (
    paragraph_longer_than_a_reader_holds,
    section_title_that_is_not_a_noun_phrase,
    sentence_longer_than_a_reader_holds,
)
from mcmr.rules.general.deterministic.manuscript.structure import (
    float_the_reader_meets_before_anything_names_it,
    numbered_statement_left_without_an_argument,
    numbered_statement_nothing_refers_to,
)

from .support import manuscript, measured, messages


def test_a_reference_forward_to_a_statement_is_reported_and_one_backward_is_not() -> None:
    """A reader cannot hold a theorem they have not reached, and can recall one they have."""
    fact = manuscript(
        ManuscriptFact,
        labels=[
            ManuscriptLabel(name="thm:late", kind="theorem", reading_order=90, line=90),
            ManuscriptLabel(name="thm:early", kind="theorem", reading_order=2, line=2),
        ],
        references=[
            ManuscriptReference(target="thm:late", command="Cref", reading_order=10, line=10),
            ManuscriptReference(target="thm:early", command="Cref", reading_order=11, line=11),
            ManuscriptReference(target="fig:plot", command="Cref", reading_order=12, line=12),
        ],
    )

    assert measured(forward_reference_to_unread_material, fact) == 1
    assert messages(forward_reference_to_unread_material, fact) == [
        "`\\Cref{thm:late}` sends the reader to a theorem first read at `:90`"
    ]


def test_a_reference_a_marked_command_spells_is_read_as_a_deliberate_pointer() -> None:
    """Naming a target in words rather than by number is how a forward pointer is written."""
    fact = manuscript(
        ManuscriptFact,
        labels=[ManuscriptLabel(name="thm:late", kind="theorem", reading_order=90, line=90)],
        references=[
            ManuscriptReference(target="thm:late", command="autoref", reading_order=10, line=10)
        ],
    )

    assert measured(forward_reference_to_unread_material, fact) == 0


def test_a_symbol_used_before_its_introduction_is_reported() -> None:
    """A symbol first met in chapter one and first defined in chapter five costs the reader."""
    fact = manuscript(
        ManuscriptNotationFact,
        symbols=[
            ManuscriptSymbol(name="\\nu", use_count=9, first_order=5, line=5),
            ManuscriptSymbol(name="\\mu", use_count=9, first_order=40, line=40),
            ManuscriptSymbol(name="k", use_count=9, first_order=1, line=1),
            ManuscriptSymbol(name="\\xi", use_count=1, first_order=1, line=1),
        ],
        sites=[
            ManuscriptSymbolSite(symbol="\\nu", reading_order=30, line=30),
            ManuscriptSymbolSite(symbol="\\mu", reading_order=30, line=30),
        ],
    )

    assert measured(symbol_used_before_it_is_introduced, fact) == 1
    assert messages(symbol_used_before_it_is_introduced, fact) == [
        "`\\nu` is used 9 times and is introduced only after the reader has met it"
    ]


def test_a_symbol_the_index_lists_is_introduced_by_the_index() -> None:
    """The notation index is the introduction of last resort, so it settles the question."""
    fact = manuscript(
        ManuscriptNotationFact,
        symbols=[ManuscriptSymbol(name="g", use_count=9, first_order=5, line=5)],
        entries=[ManuscriptEntry(symbol="g", meaning="the gain vector", line=200)],
    )

    assert measured(symbol_used_before_it_is_introduced, fact) == 0


def test_a_term_used_before_it_is_marked_is_reported() -> None:
    """A scope clause naming a word the reader has not been given is the same defect."""
    fact = manuscript(
        ManuscriptNotationFact,
        terms=[
            ManuscriptTerm(
                term="absorption",
                command="term",
                mark_order=90,
                first_use_order=10,
                use_count=4,
                line=10,
            ),
            ManuscriptTerm(
                term="binade",
                command="term",
                mark_order=5,
                first_use_order=5,
                use_count=4,
                line=5,
            ),
            ManuscriptTerm(
                term="carrier",
                command="emph",
                mark_order=90,
                first_use_order=10,
                use_count=4,
                line=10,
            ),
        ],
    )

    assert measured(term_used_before_it_is_marked, fact) == 1
    assert messages(term_used_before_it_is_marked, fact) == [
        "`absorption` is used before `\\term` marks it, 4 uses in all"
    ]


def test_an_asserting_statement_with_no_proof_and_no_head_is_reported() -> None:
    """A theorem the document never argues is the reader's oldest complaint."""
    fact = manuscript(
        ManuscriptFact,
        statements=[
            ManuscriptStatement(kind="theorem", label="thm:bare", owes_proof=True, line=10),
            ManuscriptStatement(
                kind="theorem", label="thm:proved", owes_proof=True, proof_order=12, line=20
            ),
            ManuscriptStatement(
                kind="theorem",
                label="thm:argued",
                owes_proof=True,
                discharge_head="Why it is true. Take one tree",
                line=30,
            ),
            ManuscriptStatement(kind="conjecture", label="con:open", owes_proof=True, line=40),
            ManuscriptStatement(kind="definition", label="def:one", owes_proof=False, line=50),
        ],
    )

    assert measured(numbered_statement_left_without_an_argument, fact) == 1
    assert messages(numbered_statement_left_without_an_argument, fact) == [
        "`theorem` `thm:bare` is followed by `` rather than by an argument"
    ]


def test_a_numbered_statement_nothing_references_is_reported() -> None:
    """A statement is numbered so the rest of the document can point at it."""
    fact = manuscript(
        ManuscriptFact,
        statements=[
            ManuscriptStatement(kind="lemma", label="lem:orphan", line=10),
            ManuscriptStatement(kind="lemma", label="lem:used", line=20),
            ManuscriptStatement(kind="example", label="ex:quiet", line=30),
            ManuscriptStatement(kind="lemma", label="", line=40),
        ],
        references=[ManuscriptReference(target="lem:used", command="Cref", reading_order=9)],
    )

    assert measured(numbered_statement_nothing_refers_to, fact) == 1
    assert messages(numbered_statement_nothing_refers_to, fact) == [
        "`lemma` `lem:orphan` is numbered and nothing points at it"
    ]


def test_a_float_met_before_anything_names_it_is_reported() -> None:
    """A figure with nothing to read it against is a figure a reader skips."""
    fact = manuscript(
        ManuscriptFact,
        floats=[
            ManuscriptFloat(kind="table", label="tab:orphan", reading_order=10, line=10),
            ManuscriptFloat(kind="figure", label="fig:late", reading_order=20, line=20),
            ManuscriptFloat(kind="figure", label="fig:named", reading_order=40, line=40),
            ManuscriptFloat(kind="figure", label="", reading_order=50, line=50),
        ],
        references=[
            ManuscriptReference(target="fig:late", command="Cref", reading_order=25),
            ManuscriptReference(target="fig:named", command="Cref", reading_order=30),
        ],
    )

    assert measured(float_the_reader_meets_before_anything_names_it, fact) == 2
    assert messages(float_the_reader_meets_before_anything_names_it, fact) == [
        "`table` `tab:orphan` is never referenced",
        "`figure` `fig:late` is first referenced after the reader meets it",
    ]


def test_a_widely_used_symbol_the_index_omits_is_reported() -> None:
    """An index is a promise, and an incomplete one sends a reader looking for nothing."""
    fact = manuscript(
        ManuscriptNotationFact,
        symbols=[
            ManuscriptSymbol(name="w_e", use_count=6, section_count=3, line=10),
            ManuscriptSymbol(name="\\nu", use_count=6, section_count=3, line=20),
            ManuscriptSymbol(name="r", use_count=6, section_count=1, line=30),
            ManuscriptSymbol(name="\\xi", use_count=1, section_count=3, line=40),
        ],
        entries=[
            ManuscriptEntry(symbol="\\nu", meaning="the normalized divergence", line=200),
            ManuscriptEntry(symbol="w", meaning="the sawtooth", line=201),
        ],
    )

    assert measured(symbol_missing_from_the_notation_index, fact) == 1
    assert messages(symbol_missing_from_the_notation_index, fact) == [
        "`w_e` crosses 3 sections and the notation index never lists it"
    ]


def test_a_manuscript_with_no_index_promises_nothing() -> None:
    """There is no index to be incomplete, so nothing is owed."""
    fact = manuscript(
        ManuscriptNotationFact,
        symbols=[ManuscriptSymbol(name="w_e", use_count=6, section_count=3, line=10)],
    )

    assert measured(symbol_missing_from_the_notation_index, fact) == 0


def test_an_index_row_the_body_dropped_is_reported() -> None:
    """Completeness runs both ways, and a stale row teaches something the document unsaid."""
    fact = manuscript(
        ManuscriptNotationFact,
        symbols=[ManuscriptSymbol(name="\\nu", use_count=3, line=10)],
        entries=[
            ManuscriptEntry(symbol="\\nu", meaning="the normalized divergence", line=200),
            ManuscriptEntry(symbol="\\kappa", meaning="a renamed coefficient", line=201),
        ],
    )

    assert measured(notation_entry_absent_from_the_body, fact) == 1
    assert messages(notation_entry_absent_from_the_body, fact) == [
        "the notation index lists `\\kappa` as `a renamed coefficient` and the body never sets it"
    ]


def test_a_symbol_introduced_in_two_sections_without_a_declared_sense_is_reported() -> None:
    """One symbol carrying two meanings is what a cold reader loses the most time to."""
    fact = manuscript(
        ManuscriptNotationFact,
        sites=[
            ManuscriptSymbolSite(symbol="K", section_number=1, reading_order=5, line=5),
            ManuscriptSymbolSite(symbol="K", section_number=4, reading_order=50, line=50),
            ManuscriptSymbolSite(symbol="B", section_number=1, reading_order=6, line=6),
            ManuscriptSymbolSite(symbol="B", section_number=4, reading_order=60, line=60),
            ManuscriptSymbolSite(symbol="u", section_number=2, reading_order=7, line=7),
        ],
        entries=[
            ManuscriptEntry(
                symbol="B", meaning="a matrix operand. Elsewhere a budget", sense_count=2, line=200
            )
        ],
    )

    assert measured(symbol_introduced_under_two_meanings, fact) == 1
    assert messages(symbol_introduced_under_two_meanings, fact) == [
        "`K` is introduced in 2 different sections and the index separates no senses"
    ]


def test_a_sentence_over_the_ceiling_is_reported_and_table_prose_is_not() -> None:
    """A cell holding a whole clause is not read at the pace running prose is."""
    fact = manuscript(
        ManuscriptFact,
        paragraphs=[
            ManuscriptParagraph(reading_order=1, line=1),
            ManuscriptParagraph(reading_order=2, line=2, in_cells=True),
        ],
        sentences=[
            ManuscriptSentence(reading_order=1, word_count=60, text="A long sentence", line=1),
            ManuscriptSentence(reading_order=1, word_count=12, text="A short one", line=1),
            ManuscriptSentence(reading_order=2, word_count=60, text="A long cell", line=2),
        ],
    )

    assert measured(sentence_longer_than_a_reader_holds, fact) == 1
    assert messages(sentence_longer_than_a_reader_holds, fact) == [
        "a sentence of 60 words opens `A long sentence`"
    ]


def test_a_paragraph_over_either_ceiling_is_reported() -> None:
    """Both a word count and a sentence count say a paragraph carries more than one idea."""
    fact = manuscript(
        ManuscriptFact,
        paragraphs=[
            ManuscriptParagraph(reading_order=1, line=1, word_count=300, sentence_count=6),
            ManuscriptParagraph(reading_order=2, line=2, word_count=90, sentence_count=14),
            ManuscriptParagraph(reading_order=3, line=3, word_count=46, sentence_count=3),
            ManuscriptParagraph(
                reading_order=4, line=4, word_count=300, sentence_count=20, in_float=True
            ),
        ],
    )

    assert measured(paragraph_longer_than_a_reader_holds, fact) == 2
    assert messages(paragraph_longer_than_a_reader_holds, fact) == [
        "a paragraph of 300 words over 6 sentences",
        "a paragraph of 90 words over 14 sentences",
    ]


def test_a_heading_that_asks_answers_or_sprawls_is_reported() -> None:
    """A heading names the thing under it rather than making a claim about it."""
    fact = manuscript(
        ManuscriptFact,
        sections=[
            ManuscriptSection(
                reading_order=1, line=1, title="What batching changes?", title_word_count=3
            ),
            ManuscriptSection(
                reading_order=2, line=2, title="Why the tax is a sibling", title_word_count=6
            ),
            ManuscriptSection(
                reading_order=3,
                line=3,
                title="The consequence that had to be weakened twice",
                title_word_count=8,
            ),
            ManuscriptSection(reading_order=4, line=4, title="Extremal trees", title_word_count=2),
        ],
    )

    assert measured(section_title_that_is_not_a_noun_phrase, fact) == 3
    assert messages(section_title_that_is_not_a_noun_phrase, fact) == [
        "the heading `What batching changes?` asks a question",
        "the heading `Why the tax is a sibling` answers one",
        "the heading `The consequence that had to be weakened twice` reads as a sentence",
    ]


def test_a_prose_number_that_nearly_matches_its_cited_table_is_reported() -> None:
    """The same quantity printed twice with two values is what a reader cannot reconcile."""
    fact = manuscript(
        ManuscriptEvidenceFact,
        numbers=[
            ManuscriptNumber(
                literal="0.042668",
                in_cells=True,
                float_label="tab:share",
                section_number=2,
                line=90,
            ),
            ManuscriptNumber(
                literal="0.99999",
                in_cells=True,
                float_label="tab:share",
                section_number=2,
                line=91,
            ),
            ManuscriptNumber(literal="0.042399", section_number=1, line=10),
            ManuscriptNumber(literal="0.042668", section_number=1, line=11),
            ManuscriptNumber(literal="9.999999", section_number=1, line=12),
        ],
        references=[
            ManuscriptReference(
                target="tab:share", command="Cref", section_number=1, reading_order=5
            )
        ],
    )

    assert measured(prose_number_that_nearly_matches_its_table, fact) == 1
    assert messages(prose_number_that_nearly_matches_its_table, fact) == [
        "prose states `0.042399` where the nearest referenced cell reads `0.042668`"
    ]


def test_a_ratio_printed_without_its_parts_is_reported() -> None:
    """Two different pairs of measurements give the same quotient, and only one was taken."""
    fact = manuscript(
        ManuscriptEvidenceFact,
        numbers=[
            ManuscriptNumber(literal="0.1456", names_ratio=True, sentence_number_count=1, line=10),
            ManuscriptNumber(literal="0.1456", names_ratio=True, sentence_number_count=3, line=20),
            ManuscriptNumber(
                literal="0.1456", names_ratio=False, sentence_number_count=1, line=30
            ),
            ManuscriptNumber(
                literal="0.1456",
                names_ratio=True,
                sentence_number_count=1,
                in_cells=True,
                line=40,
            ),
        ],
    )

    assert measured(ratio_published_without_its_parts, fact) == 1
    assert messages(ratio_published_without_its_parts, fact) == [
        "`0.1456` is named as a derived quantity beside 0 other numbers"
    ]


def test_an_unpinned_citation_beside_a_measurement_is_reported() -> None:
    """A work of two hundred pages with no locator is a promise nobody can keep."""
    fact = manuscript(
        ManuscriptEvidenceFact,
        numbers=[
            ManuscriptNumber(literal="3.83", reading_order=10, line=10),
            ManuscriptNumber(literal="9.99", reading_order=90, line=90),
        ],
        citations=[
            ManuscriptCitation(key="bare2026", pin="", reading_order=11, line=11),
            ManuscriptCitation(key="pinned2026", pin="Table 2", reading_order=12, line=12),
            ManuscriptCitation(key="distant2026", pin="", reading_order=50, line=50),
        ],
    )

    assert measured(measurement_resting_on_an_unpinned_citation, fact) == 1
    assert messages(measurement_resting_on_an_unpinned_citation, fact) == [
        "`bare2026` supports `3.83` and names no page or section"
    ]


def test_a_manuscript_record_locates_itself_in_the_file_it_was_read_from() -> None:
    """A finding names a place an editor can open, which every record has to be able to say."""
    label = ManuscriptLabel(name="thm:one", kind="theorem", path="sections/10.tex", line=42)

    assert label.span.location == "sections/10.tex:42"
