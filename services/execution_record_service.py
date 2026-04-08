from __future__ import annotations

from domain.models.base import utc_now
from domain.models.execution_record import ExecutionRecord
from domain.rules.statuses import ExecutionRecordStatus
from services.base import BaseService
from services.errors import EntityNotFoundError


class ExecutionRecordService(BaseService):
    def start(self, *, capability_name: str, provider_name: str, input_ref: str) -> ExecutionRecord:
        record = ExecutionRecord(
            capability_name=capability_name,
            provider_name=provider_name,
            input_ref=input_ref,
            status=ExecutionRecordStatus.PENDING,
        )
        return self.repository.add(record)

    def succeed(self, *, record_id: str, output_ref: str | None = None) -> ExecutionRecord:
        record = self.repository.get(ExecutionRecord, record_id)
        if record is None:
            raise EntityNotFoundError(f"ExecutionRecord not found: {record_id}")

        record.status = ExecutionRecordStatus.SUCCEEDED
        record.output_ref = output_ref
        record.ended_at = utc_now()
        return self.repository.update(record)

    def fail(self, *, record_id: str, output_ref: str | None = None) -> ExecutionRecord:
        record = self.repository.get(ExecutionRecord, record_id)
        if record is None:
            raise EntityNotFoundError(f"ExecutionRecord not found: {record_id}")

        record.status = ExecutionRecordStatus.FAILED
        record.output_ref = output_ref
        record.ended_at = utc_now()
        return self.repository.update(record)
