"""Tests for the Pydantic → TypeScript codegen.

Includes the load-bearing drift check: the committed
`app/sandbox_web/src/generated_types.ts` file must match what `generate()` would
produce now. CI and pre-commit run the same check via `--check`; running the
test suite catches drift locally too.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field
from sandbox_core.tools.generate_types import (
    DEFAULT_OUT,
    emit_enum,
    emit_model,
    generate,
    main,
    ts_type,
)

REQUIRED_EXPORTS = (
    "BaseLayout",
    "BuildingPlacement",
    "DeploymentAction",
    "DeploymentPlan",
    "WorldState",
    "TickFrame",
    "Replay",
    "Score",
    "Event",
    "BuildingType",
    "TroopType",
    "SpellType",
    "Projectile",
    "SpellCast",
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_generate_includes_required_exports() -> None:
    output = generate()
    for name in REQUIRED_EXPORTS:
        assert f"export interface {name} " in output, f"missing interface {name}"


def test_generate_is_idempotent() -> None:
    assert generate() == generate()


def test_generate_emits_strenum_unions() -> None:
    output = generate()
    assert "export type BuildingCategory =" in output
    assert '"town_hall"' in output
    assert '"defense"' in output


def test_generate_emits_schema_version_constant() -> None:
    assert "export const SCHEMA_VERSION = 3;" in generate()


def test_committed_file_matches_generator() -> None:
    """The committed generated_types.ts must match what `generate()` produces.

    If this fails, run `uv run python -m sandbox_core.tools.generate_types`
    and commit the result.
    """
    committed_path = REPO_ROOT / DEFAULT_OUT
    assert committed_path.exists(), (
        f"{committed_path} does not exist — run "
        "`uv run python -m sandbox_core.tools.generate_types` and commit it."
    )
    committed = committed_path.read_text(encoding="utf-8")
    assert committed == generate(), (
        "generated_types.ts is out of date with sandbox_core/schemas.py. "
        "Run `uv run python -m sandbox_core.tools.generate_types` and commit the result."
    )


# ---------------------------------------------------------------------------
# Type-conversion unit tests against synthetic models
# ---------------------------------------------------------------------------


def test_ts_type_primitives() -> None:
    assert ts_type(int) == "number"
    assert ts_type(float) == "number"
    assert ts_type(str) == "string"
    assert ts_type(bool) == "boolean"
    assert ts_type(Any) == "unknown"


def test_ts_type_optional_and_union() -> None:
    assert ts_type(int | None) == "number | null"
    assert ts_type(str | int) == "string | number"


def test_ts_type_list_and_tuple_and_dict() -> None:
    assert ts_type(list[int]) == "number[]"
    assert ts_type(tuple[int, int]) == "[number, number]"
    assert ts_type(tuple[float, ...]) == "number[]"
    assert ts_type(dict[str, float]) == "{ [key: string]: number }"
    assert ts_type(dict[str, Any]) == "{ [key: string]: unknown }"


def test_ts_type_literal_values() -> None:
    assert ts_type(Literal[1]) == "1"
    assert ts_type(Literal["a", "b"]) == '"a" | "b"'


def test_ts_type_rejects_non_string_dict_keys() -> None:
    with pytest.raises(TypeError):
        ts_type(dict[int, int])


def test_emit_model_uses_field_declaration_order() -> None:
    class Sample(BaseModel):
        a: int
        b: str
        c: list[float] = Field(default_factory=lambda: list[float]())

    output = emit_model(Sample)
    a_idx = output.index("a:")
    b_idx = output.index("b:")
    c_idx = output.index("c:")
    assert a_idx < b_idx < c_idx
    assert "a: number;" in output
    assert "b: string;" in output
    assert "c: number[];" in output


def test_emit_enum_sorts_members_for_stable_output() -> None:
    class Color(StrEnum):
        RED = "red"
        BLUE = "blue"
        GREEN = "green"

    output = emit_enum(Color)
    # Sorted alphabetically by value: blue < green < red
    blue = output.index('"blue"')
    green = output.index('"green"')
    red = output.index('"red"')
    assert blue < green < red


# ---------------------------------------------------------------------------
# CLI behavior
# ---------------------------------------------------------------------------


def test_check_mode_passes_on_committed_file(tmp_path: Path) -> None:
    out = tmp_path / "generated.ts"
    out.write_text(generate(), encoding="utf-8")
    assert main(["--check", "--out", str(out)]) == 0


def test_check_mode_fails_on_drift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "generated.ts"
    out.write_text("// stale\n", encoding="utf-8")
    assert main(["--check", "--out", str(out)]) == 1
    err = capsys.readouterr().err
    assert "out of date" in err


def test_check_mode_fails_when_file_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "missing.ts"
    assert main(["--check", "--out", str(out)]) == 1
    err = capsys.readouterr().err
    assert "does not exist" in err


def test_write_mode_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "generated.ts"
    assert main(["--out", str(out)]) == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8") == generate()
