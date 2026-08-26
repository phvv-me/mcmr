from .citation import ManuscriptCitation
from .entry import ManuscriptEntry
from .evidence import ManuscriptEvidenceFact
from .fact import ManuscriptFact
from .float import ManuscriptFloat
from .label import ManuscriptLabel
from .notation import ManuscriptNotationFact
from .number import ManuscriptNumber
from .paragraph import ManuscriptParagraph
from .place import ManuscriptPlace
from .reference import ManuscriptReference
from .section import ManuscriptSection
from .sentence import ManuscriptSentence
from .site import ManuscriptSymbolSite
from .statement import ManuscriptStatement
from .symbol import ManuscriptSymbol
from .term import ManuscriptTerm

ManuscriptFact.model_rebuild(
    _types_namespace={
        "ManuscriptFloat": ManuscriptFloat,
        "ManuscriptLabel": ManuscriptLabel,
        "ManuscriptParagraph": ManuscriptParagraph,
        "ManuscriptReference": ManuscriptReference,
        "ManuscriptSection": ManuscriptSection,
        "ManuscriptSentence": ManuscriptSentence,
        "ManuscriptStatement": ManuscriptStatement,
    }
)
ManuscriptNotationFact.model_rebuild(
    _types_namespace={
        "ManuscriptEntry": ManuscriptEntry,
        "ManuscriptSymbol": ManuscriptSymbol,
        "ManuscriptSymbolSite": ManuscriptSymbolSite,
        "ManuscriptTerm": ManuscriptTerm,
    }
)
ManuscriptEvidenceFact.model_rebuild(
    _types_namespace={
        "ManuscriptCitation": ManuscriptCitation,
        "ManuscriptNumber": ManuscriptNumber,
        "ManuscriptReference": ManuscriptReference,
    }
)

__all__ = [
    "ManuscriptCitation",
    "ManuscriptEntry",
    "ManuscriptEvidenceFact",
    "ManuscriptFact",
    "ManuscriptFloat",
    "ManuscriptLabel",
    "ManuscriptNotationFact",
    "ManuscriptNumber",
    "ManuscriptParagraph",
    "ManuscriptPlace",
    "ManuscriptReference",
    "ManuscriptSection",
    "ManuscriptSentence",
    "ManuscriptStatement",
    "ManuscriptSymbol",
    "ManuscriptSymbolSite",
    "ManuscriptTerm",
]
