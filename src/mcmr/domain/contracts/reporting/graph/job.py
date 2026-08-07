from patos import FrozenModel

from ....primitives import NonEmptyStr


class RuleJob(FrozenModel):
    """State one executed rule as the job that read its declared fact datasets."""

    rule: NonEmptyStr
    callable: str = ""
    summary: str = ""
    inputs: list[str] = []
    primary: str = ""
