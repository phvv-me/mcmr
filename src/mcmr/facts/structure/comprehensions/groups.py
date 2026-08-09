from patos import FrozenModel
from pydantic import Field, NonNegativeInt

from ...foundation import NodeRef


class SetLoopFields(FrozenModel):
    """Retain initialization, loop shape, and its first source node."""

    name: str = Field(default="", description="local name of the set the loop populates")
    has_unshadowed_set_initialization: bool = Field(
        description="whether name is assigned the unshadowed builtin set() right before the loop"
    )
    loop_is_synchronous: bool = Field(
        description="whether the following for loop iterating into the set is not async"
    )
    only_effect_is_add: bool = Field(
        description="whether the loop's only effect is one name.add(expression) call"
    )
    conditional_count: NonNegativeInt = Field(
        default=0, description="number of if conditions guarding the add call"
    )
    has_else: bool = Field(
        default=False, description="whether the guarding if branch carries an else clause"
    )
    initialization: NodeRef | None = Field(
        default=None, description="syntax node of the set initialization statement"
    )
