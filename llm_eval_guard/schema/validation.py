"""Generic output-contract validation: does an LLM's JSON output match a caller-supplied schema?

Why a metric instead of a bare `model_validate()` call in the caller's own test: wrapping it as a
`Metric` means schema checks compose with everything else in the runner/reporting layer (Phase 3.3)
the same way faithfulness/relevancy do — one `EvalCase` in, one `MetricResult` out.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from llm_eval_guard.core.metric import Metric
from llm_eval_guard.core.models import EvalCase, MetricResult

_ExtraPolicy = Literal["forbid", "allow"]

# schema -> extra-fields policy -> policy-specific subclass. Keyed on the caller's original class,
# never mutated in place (see _policy_variant's docstring for why).
_POLICY_CACHE: dict[tuple[type[BaseModel], _ExtraPolicy], type[BaseModel]] = {}


def _policy_variant(schema: type[BaseModel], extra: _ExtraPolicy) -> type[BaseModel]:
    """Return a subclass of `schema` with its extra-fields handling overridden to `extra`.

    Why a subclass instead of mutating `schema.model_config` in place: the caller's schema class
    may be shared (e.g. one `RagAnswer` reused by a strict and a lenient
    `SchemaValidationMetric` in the same process) — mutating it in place would make one metric's
    mode leak into the other's.
    """
    key = (schema, extra)
    if key not in _POLICY_CACHE:
        _POLICY_CACHE[key] = type(
            f"{schema.__name__}__{extra}",
            (schema,),
            {"model_config": ConfigDict(extra=extra)},
        )
    return _POLICY_CACHE[key]


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors():
        loc = ".".join(str(p) for p in error["loc"]) or "<root>"
        parts.append(f"{loc}: {error['msg']}")
    return "; ".join(parts)


class SchemaValidationMetric(Metric):
    """Validates `case.actual_output` (parsed as JSON) against `schema`.

    `strict=True` (default): any schema violation — missing required field, wrong type, or an
    extra field — fails the case.

    `strict=False` ("lenient"): extra fields and validation errors (e.g. a missing required
    field) are recorded in `reason` as warnings rather than failing the case — only an
    unparseable payload fails, since that's not a schema question at all, there's no payload to
    check a schema against.
    """

    def __init__(
        self, schema: type[BaseModel], *, strict: bool = True, threshold: float = 1.0
    ) -> None:
        super().__init__(threshold=threshold)
        self._schema = schema
        self._strict = strict

    @property
    def name(self) -> str:
        return f"schema:{self._schema.__name__}"

    def evaluate(self, case: EvalCase) -> MetricResult:
        try:
            payload = json.loads(case.actual_output)
        except json.JSONDecodeError as exc:
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                reason=f"invalid JSON: {exc}",
            )

        variant = _policy_variant(self._schema, "forbid" if self._strict else "allow")
        try:
            variant.model_validate(payload)
        except ValidationError as exc:
            reason = _format_validation_error(exc)
            if self._strict:
                return MetricResult(metric_name=self.name, score=0.0, passed=False, reason=reason)
            return MetricResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                reason=f"lenient mode — schema warnings: {reason}",
            )

        if not self._strict and isinstance(payload, dict):
            extra_keys = sorted(set(payload) - set(self._schema.model_fields))
            if extra_keys:
                reason = f"lenient mode — schema warnings: unexpected fields ignored: {extra_keys}"
                return MetricResult(metric_name=self.name, score=1.0, passed=True, reason=reason)

        return MetricResult(metric_name=self.name, score=1.0, passed=True, reason=None)
