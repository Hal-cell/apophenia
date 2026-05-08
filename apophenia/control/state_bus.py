"""StateBus — mailbox for the live `VisualState`.

The control UI sends partial JSON updates via HTTP `PATCH /api/state`;
they merge into the StateBus. The render process and the WS broadcaster
read snapshots of the state — render uses it for per-frame uniforms
(freeze / channel weights / palette), the WS broadcaster echoes it
back to the UI so external state changes (e.g. preset recall) propagate
to all connected browsers.

Same single-slot pattern as `FeatureBus` and `SlowBus`: one current
state, mutex-guarded read/write, no history. Pydantic validates every
write so the schema in `apophenia.state.VisualState` is the single
source of truth — bad partial dicts are rejected at update time, not
silently coerced.
"""

from __future__ import annotations

import threading
from typing import Any

from apophenia.state import VisualState


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `update` into a copy of `base`.

    Dict values merge field-by-field. Anything else (lists, scalars)
    replaces the corresponding base value wholesale. The `update` dict
    is the partial diff coming from the UI, so mismatched types
    (e.g. UI sends `channel_weight` as a list of 14 floats) replace
    cleanly.
    """
    out = dict(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class StateBus:
    """Thread-safe single-slot mailbox holding the current `VisualState`.

    Writers go through `update(partial)` (deep-merge + Pydantic
    validation) or `replace(state)` (whole-state swap, e.g. preset
    recall). Readers go through `get()` which returns a defensive
    copy so they can iterate without holding the lock.
    """

    def __init__(self, initial: VisualState | None = None) -> None:
        self._lock = threading.Lock()
        # Pydantic Field() defaults aren't seen by mypy without the plugin;
        # all VisualState fields have defaults so this constructs cleanly.
        self._state = initial if initial is not None else VisualState()  # type: ignore[call-arg]

    def get(self) -> VisualState:
        """Return a snapshot of the current state."""
        with self._lock:
            return self._state.model_copy(deep=True)

    def replace(self, new_state: VisualState) -> VisualState:
        """Overwrite the current state. Used by preset recall and on
        startup to seed from a saved session.
        """
        with self._lock:
            self._state = new_state.model_copy(deep=True)
            return self._state.model_copy(deep=True)

    def update(self, partial: dict[str, Any]) -> VisualState:
        """Apply a partial dict update.

        Raises pydantic.ValidationError if the merged state is invalid.
        Returns the new state on success.
        """
        with self._lock:
            current = self._state.model_dump()
            merged = _deep_merge(current, partial)
            new_state = VisualState.model_validate(merged)
            self._state = new_state
            return self._state.model_copy(deep=True)
