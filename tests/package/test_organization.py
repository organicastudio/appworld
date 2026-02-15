from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "appworld" / "common" / "organization.py"
SPEC = importlib.util.spec_from_file_location("appworld_common_organization", MODULE_PATH)
assert SPEC and SPEC.loader
organization = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = organization
SPEC.loader.exec_module(organization)

apply_plan = organization.apply_plan
build_organization_plan = organization.build_organization_plan
render_plan_tree = organization.render_plan_tree


class TestOrganizationPlan:
    def test_plan_contains_mirrored_libraries(self, tmp_path: Path) -> None:
        plan = build_organization_plan(base=tmp_path, library_names=["alpha"])

        libraries_folder = next(folder for folder in plan.folders if folder.name == "libraries")
        alpha_spec = next(folder for folder in libraries_folder.children if folder.name == "alpha")
        child_names = {child.name for child in alpha_spec.children}
        assert {"source", "mirror"}.issubset(child_names)

    def test_render_plan_tree_produces_tree(self, tmp_path: Path) -> None:
        plan = build_organization_plan(base=tmp_path)
        tree = render_plan_tree(plan)
        assert tree.children, "Expected rendered tree to include top-level folders"

    def test_apply_plan_dry_run_records_plan(self, tmp_path: Path) -> None:
        plan = build_organization_plan(base=tmp_path, library_names=["alpha"])
        result = apply_plan(plan, dry_run=True)
        assert result.dry_run is True
        assert any(path.match("*/libraries") for path in result.planned_dirs)
        assert not (tmp_path / "libraries").exists()

    def test_apply_plan_creates_directories(self, tmp_path: Path) -> None:
        plan = build_organization_plan(base=tmp_path, library_names=["alpha"], include_nft=False)
        result = apply_plan(plan, dry_run=False)

        assert result.dry_run is False
        assert (tmp_path / "libraries" / "alpha" / "source").is_dir()
        assert (tmp_path / "libraries" / "alpha" / "mirror").is_dir()
        assert (tmp_path / "libraries" / "alpha" / "docs" / "README.md").is_file()

        # Re-running should mark items as existing rather than attempting recreation.
        second_result = apply_plan(plan, dry_run=False)
        assert second_result.existing_dirs
        assert second_result.existing_files
