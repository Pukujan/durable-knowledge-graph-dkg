from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from fossil_core.ports.projection import ProjectionReceipt
from fossil_core.projection.migration import ordered_events


@dataclass(frozen=True)
class ProjectorCycle:
    """Machine-testable summary of one deterministic projector scan."""

    scanned: int
    receipts: tuple[ProjectionReceipt, ...]

    @property
    def applied(self) -> int:
        return sum(receipt.status == "applied" for receipt in self.receipts)

    @property
    def skipped(self) -> int:
        return sum(receipt.status == "skipped" for receipt in self.receipts)

    @property
    def redacted(self) -> int:
        return sum(receipt.status == "redacted" for receipt in self.receipts)

    @property
    def failed(self) -> int:
        return sum(receipt.status == "failed" for receipt in self.receipts)


class ProjectorWorker:
    """Continuously materialize accepted durable events into one projection build.

    Durable event acceptance is upstream of this worker. A projection failure is
    therefore recorded and retried; it never rolls back or rewrites canonical
    truth. Events are scanned in corpus commit order. If one pending event fails,
    the current cycle stops before later events so lifecycle materialization cannot
    silently advance past an earlier failed event.
    """

    def __init__(
        self,
        *,
        event_store: Any,
        projection: Any,
        ledger: Any,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("projector poll_interval_seconds must be positive")
        self.event_store = event_store
        self.projection = projection
        self.ledger = ledger
        self.poll_interval_seconds = float(poll_interval_seconds)

    def _skip_receipt(self, event_id: str, detail: str) -> ProjectionReceipt:
        return ProjectionReceipt(
            self.projection.name,
            self.projection.version,
            event_id,
            "skipped",
            detail,
        )

    async def run_once_async(self) -> ProjectorCycle:
        receipts: list[ProjectionReceipt] = []

        purge_event_redactions = getattr(
            self.projection, "purge_event_redactions_async", None
        )
        if callable(purge_event_redactions):
            purge_receipts = await purge_event_redactions(event_store=self.event_store)
            receipts.extend(purge_receipts)
            if any(receipt.status == "failed" for receipt in purge_receipts):
                return ProjectorCycle(scanned=0, receipts=tuple(receipts))

        events = ordered_events(self.event_store.iter_events())
        scanned = 0
        for event in events:
            scanned += 1
            event_id = str(event["event_id"])

            if self.ledger.is_redacted(event_id):
                receipts.append(self._skip_receipt(event_id, "projection redacted"))
                continue
            if self.ledger.is_applied(event_id):
                receipts.append(self._skip_receipt(event_id, "already applied"))
                continue

            receipt = await self.projection.apply_event_async(event)
            receipts.append(receipt)
            if receipt.status == "failed":
                break

        return ProjectorCycle(scanned=scanned, receipts=tuple(receipts))

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        """Run restartably until requested to stop.

        Waiting is interruptible by ``stop_event`` so shutdown does not need to
        wait for the polling interval to expire. Any event not durably marked as
        applied remains eligible for the next cycle or process restart.
        """

        while not stop_event.is_set():
            await self.run_once_async()
            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=self.poll_interval_seconds
                )
            except TimeoutError:
                continue


__all__ = ["ProjectorCycle", "ProjectorWorker"]
