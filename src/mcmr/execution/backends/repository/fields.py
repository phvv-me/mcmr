from patos import FrozenModel


class RepositoryAnswerFields(FrozenModel):
    """Carry one compact answer after schema validation."""

    values: list[str]
    reasoning: str
    citations: list[str]
    confidence: float
