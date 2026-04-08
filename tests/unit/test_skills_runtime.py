from __future__ import annotations

from adapters.providers.base import CapabilityCallResult
from domain.models.execution_record import ExecutionRecord
from services.execution_record_service import ExecutionRecordService
from skills import CapabilityRuntime, FallbackPolicy, ProviderRouter, build_default_registry
from tests.support import IsolatedTestCase


class AlwaysFailContentProvider:
    provider_name = "test.fail-content"
    capabilities = ("content_generation",)

    def invoke(self, capability_name: str, payload: dict[str, object]) -> CapabilityCallResult:
        raise RuntimeError("simulated provider failure")


class AlwaysPassContentProvider:
    provider_name = "test.pass-content"
    capabilities = ("content_generation",)

    def invoke(self, capability_name: str, payload: dict[str, object]) -> CapabilityCallResult:
        return CapabilityCallResult(
            capability_name=capability_name,
            provider_name=self.provider_name,
            payload={
                "variant_type": payload.get("variant_type", "post"),
                "platform": payload.get("platform", "xiaohongshu"),
                "title": "runtime-generated-title",
                "body": "runtime-generated-body",
                "style_profile": None,
            },
            output_ref="test.pass-content:content_generation",
        )


class TestSkillsRuntime(IsolatedTestCase):
    def test_runtime_fallback_and_execution_record_write(self):
        runtime = CapabilityRuntime(
            registry=build_default_registry(),
            router=ProviderRouter([AlwaysFailContentProvider(), AlwaysPassContentProvider()]),
            fallback_policy=FallbackPolicy(),
            execution_records=ExecutionRecordService(db_path=self.db_path),
        )

        result = runtime.execute(
            capability_name="content_generation",
            payload={
                "platform": "xiaohongshu",
                "variant_type": "post",
            },
        )

        self.assertEqual(result.provider_name, "test.pass-content")
        records = ExecutionRecordService(db_path=self.db_path).repository.list(
            ExecutionRecord,
            order_by="started_at ASC",
        )
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].provider_name, "test.fail-content")
        self.assertEqual(records[0].status.value, "FAILED")
        self.assertEqual(records[1].provider_name, "test.pass-content")
        self.assertEqual(records[1].status.value, "SUCCEEDED")
