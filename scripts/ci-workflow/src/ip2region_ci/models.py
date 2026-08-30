"""Strict manifest models for CI components."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Platform = Literal["linux", "macos", "windows"]
ComponentKind = Literal["binding", "maker", "alias", "unsupported"]


class Step(BaseModel):
    """One executable build or test step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    command: tuple[str, ...] = Field(min_length=1)
    timeout_seconds: int = Field(default=600, ge=1, le=7200)
    environment: dict[str, str] = Field(default_factory=dict)


class Component(BaseModel):
    """A runnable, aliased, or intentionally unavailable repository component."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    kind: ComponentKind
    path: str = Field(pattern=r"^(binding|maker)/[a-z0-9_]+$")
    platforms: frozenset[Platform] = Field(default_factory=frozenset)
    steps: tuple[Step, ...] = ()
    alias_of: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_kind_contract(self) -> Self:
        """Ensure each component kind carries exactly the state it needs."""
        if self.kind in {"binding", "maker"}:
            if not self.platforms or not self.steps:
                msg = f"runnable component {self.id} needs platforms and steps"
                raise ValueError(msg)
            if self.alias_of is not None or self.reason is not None:
                msg = f"runnable component {self.id} cannot set alias_of or reason"
                raise ValueError(msg)
        elif self.kind == "alias":
            if self.alias_of is None or self.steps or self.platforms or self.reason is not None:
                msg = f"alias component {self.id} must only set alias_of"
                raise ValueError(msg)
        elif self.reason is None or self.steps or self.platforms or self.alias_of is not None:
            msg = f"unsupported component {self.id} must only set reason"
            raise ValueError(msg)
        return self

    @property
    def runnable(self) -> bool:
        """Return whether this component owns executable CI steps."""
        return self.kind in {"binding", "maker"}


class Manifest(BaseModel):
    """Top-level CI component manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal[1]
    component_roots: tuple[str, ...] = Field(min_length=1)
    components: tuple[Component, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identifiers(self) -> Self:
        """Reject duplicate IDs and repository paths."""
        ids = [component.id for component in self.components]
        paths = [component.path for component in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("component IDs must be unique")
        if len(paths) != len(set(paths)):
            raise ValueError("component paths must be unique")
        return self
