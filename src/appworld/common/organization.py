"""Utilities for building opinionated folder organizations.

This module provides helpers to design and optionally materialize a
folder layout geared towards mirrored software-chain libraries, NFT
asset organization, and FastAPI-based workflow automation. The
functions intentionally avoid heavyweight dependencies so the layout can
be previewed with minimal token (command) usage in interactive coding
sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, MutableSequence, Sequence

try:  # pragma: no cover - optional rich dependency
    from rich.tree import Tree
except ModuleNotFoundError:  # pragma: no cover - fallback used in minimal environments
    class Tree:  # type: ignore[override]
        """Lightweight fallback for :class:`rich.tree.Tree`."""

        def __init__(self, label: str):
            self.label = label
            self.children: list["Tree"] = []

        def add(self, label: str) -> "Tree":
            child = Tree(label)
            self.children.append(child)
            return child


@dataclass(frozen=True)
class FolderSpec:
    """Blueprint describing a folder, its files, and nested folders."""

    name: str
    children: Sequence["FolderSpec"] = field(default_factory=tuple)
    files: Sequence[str] = field(default_factory=tuple)
    description: str | None = None

    def __post_init__(self) -> None:  # pragma: no cover - dataclass boilerplate
        object.__setattr__(self, "children", tuple(self.children))
        object.__setattr__(self, "files", tuple(self.files))

    def add_to_tree(self, tree: Tree) -> None:
        """Append this node to the given rich tree."""

        label = self.name
        if self.description:
            label = f"{label} — {self.description}"
        branch = tree.add(label)
        for file_name in self.files:
            branch.add(file_name)
        for child in self.children:
            child.add_to_tree(branch)


@dataclass(frozen=True)
class OrganizationPlan:
    """High level description of a folder organization plan."""

    base_path: Path
    folders: Sequence[FolderSpec]
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:  # pragma: no cover - dataclass boilerplate
        object.__setattr__(self, "base_path", Path(self.base_path))
        object.__setattr__(self, "folders", tuple(self.folders))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass
class OrganizationResult:
    """Result of materializing an :class:`OrganizationPlan`."""

    dry_run: bool
    created_dirs: MutableSequence[Path] = field(default_factory=list)
    created_files: MutableSequence[Path] = field(default_factory=list)
    existing_dirs: MutableSequence[Path] = field(default_factory=list)
    existing_files: MutableSequence[Path] = field(default_factory=list)
    planned_dirs: MutableSequence[Path] = field(default_factory=list)
    planned_files: MutableSequence[Path] = field(default_factory=list)


def render_plan_tree(plan: OrganizationPlan) -> Tree:
    """Render the plan as a :class:`rich.tree.Tree` for display."""

    root_label = f"[bold]{plan.base_path}[/bold]"
    tree = Tree(root_label)
    for folder in plan.folders:
        folder.add_to_tree(tree)
    return tree


def apply_plan(plan: OrganizationPlan, *, dry_run: bool = False) -> OrganizationResult:
    """Create directories and files described in ``plan``.

    Parameters
    ----------
    plan:
        Organization plan to materialize.
    dry_run:
        When ``True`` the operation only records the directories/files that
        would be created.
    """

    result = OrganizationResult(dry_run=dry_run)

    for folder in plan.folders:
        _apply_folder(
            base_path=plan.base_path,
            spec=folder,
            result=result,
            dry_run=dry_run,
        )

    return result


def build_organization_plan(
    *,
    base: Path,
    library_names: Sequence[str] | None = None,
    include_fast_api: bool = True,
    include_nft: bool = True,
) -> OrganizationPlan:
    """Create the default AppWorld organic folder organization plan."""

    normalized_base = Path(base)

    library_names = tuple(dict.fromkeys(library_names or ("core", "integrations", "compliance")))
    libraries = tuple(_library_spec(name) for name in library_names)

    workflow_children: list[FolderSpec] = [
        FolderSpec("automation", description="Reusable orchestration primitives"),
        FolderSpec(
            "pipelines",
            description="Multi-step software chains for cross-app coordination",
            children=(
                FolderSpec("ingest"),
                FolderSpec("transform"),
                FolderSpec("publish"),
            ),
        ),
    ]
    if include_fast_api:
        workflow_children.append(_fastapi_workflow_spec())

    nft_children: Iterable[FolderSpec] = ()
    if include_nft:
        nft_children = (
            FolderSpec(
                "collections",
                description="NFT drops grouped by campaign",
                children=(
                    FolderSpec("metadata", files=("schema.json", "collection.yaml")),
                    FolderSpec("assets"),
                    FolderSpec("proofs"),
                ),
            ),
            FolderSpec(
                "registry",
                description="Minted token manifests and supply tracking",
                files=("index.json",),
            ),
            FolderSpec(
                "workflows",
                description="Automation around NFT lifecycle",
                children=(
                    FolderSpec("mint"),
                    FolderSpec("distribute"),
                    FolderSpec("reconcile"),
                ),
            ),
        )

    folders = (
        FolderSpec(
            "libraries",
            description="Software-chain libraries with mirrored source trees",
            children=libraries,
        ),
        FolderSpec(
            "workflows",
            description="Operational workflows and service automations",
            children=tuple(workflow_children),
        ),
        FolderSpec(
            "apis",
            description="External and internal API surface",
            children=(
                FolderSpec("http", description="REST and webhook interfaces"),
                FolderSpec("events", description="Async/pub-sub contracts"),
            ),
        ),
        FolderSpec(
            "infrastructure",
            description="Deployment, IaC, and observability",
            children=(
                FolderSpec("iac"),
                FolderSpec("monitoring"),
                FolderSpec("config"),
            ),
        ),
    )

    if include_nft:
        folders += (
            FolderSpec(
                "digital_assets",
                description="NFT and media organization",
                children=tuple(nft_children),
            ),
        )

    metadata: Mapping[str, str] = {
        "libraries": "Mirrored source trees keep prod and sandbox implementations in sync.",
        "workflows": "Workflows emphasise minimal-step chains to conserve token usage.",
    }

    return OrganizationPlan(base_path=normalized_base, folders=folders, metadata=metadata)


def _apply_folder(
    *,
    base_path: Path,
    spec: FolderSpec,
    result: OrganizationResult,
    dry_run: bool,
) -> None:
    folder_path = base_path / spec.name
    if folder_path.exists():
        result.existing_dirs.append(folder_path)
    else:
        if dry_run:
            result.planned_dirs.append(folder_path)
        else:
            folder_path.mkdir(parents=True, exist_ok=True)
            result.created_dirs.append(folder_path)

    for file_name in spec.files:
        file_path = folder_path / file_name
        if file_path.exists():
            result.existing_files.append(file_path)
        else:
            if dry_run:
                result.planned_files.append(file_path)
            else:
                file_path.touch()
                result.created_files.append(file_path)

    for child in spec.children:
        _apply_folder(
            base_path=folder_path,
            spec=child,
            result=result,
            dry_run=dry_run,
        )


def _library_spec(name: str) -> FolderSpec:
    mirrored_children = _mirrored_children()
    return FolderSpec(
        name,
        description=f"Library '{name}' with mirrored implementations",
        children=(
            FolderSpec(
                "source",
                description="Primary implementation",
                children=mirrored_children,
            ),
            FolderSpec(
                "mirror",
                description="Sandboxed mirror for validation and safety",
                children=mirrored_children,
            ),
            FolderSpec("tests"),
            FolderSpec("docs", files=("README.md",)),
        ),
    )


def _mirrored_children() -> tuple[FolderSpec, ...]:
    return (
        FolderSpec("adapters", description="External service connectors"),
        FolderSpec("domain", description="Core domain models"),
        FolderSpec("services", description="Business logic services"),
        FolderSpec("pipelines", description="Composable software chains"),
    )


def _fastapi_workflow_spec() -> FolderSpec:
    return FolderSpec(
        "fastapi",
        description="FastAPI application workflows",
        children=(
            FolderSpec("routers"),
            FolderSpec("schemas"),
            FolderSpec("dependencies"),
            FolderSpec("services"),
            FolderSpec("tests"),
        ),
        files=("settings.py",),
    )


__all__ = [
    "FolderSpec",
    "OrganizationPlan",
    "OrganizationResult",
    "apply_plan",
    "build_organization_plan",
    "render_plan_tree",
]
