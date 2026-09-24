"""
Unit tests for the Python programmatic gcloud client wrapper (client.py).
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from client import (
    GcloudClient,
    GcloudCommandError,
    GcloudTimeoutError,
)


class TestGcloudPythonClient(unittest.TestCase):
    def test_build_args(self) -> None:
        client = GcloudClient(
            project="test-proj-456",
            impersonate_service_account="runner@test-proj-456.iam.gserviceaccount.com",
            configuration="staging-profile",
            binary_path="/usr/local/bin/gcloud",
        )

        args = client.build_args(["compute", "instances", "list"], format_spec="json")
        expected = [
            "/usr/local/bin/gcloud",
            "compute",
            "instances",
            "list",
            "--project=test-proj-456",
            "--impersonate-service-account=runner@test-proj-456.iam.gserviceaccount.com",
            "--configuration=staging-profile",
            "--quiet",
            "--format=json",
        ]
        self.assertEqual(args, expected)

    def test_build_filter(self) -> None:
        terms = {"status": "RUNNING", "zone": "us-central1-*"}
        expr = GcloudClient.build_filter(terms)
        self.assertIn("status=RUNNING", expr)
        self.assertIn("zone:us-central1-*", expr)
        self.assertIn(" AND ", expr)

    def test_list_instances_success(self) -> None:
        mock_payload = """[
            {
                "id": "2001",
                "name": "api-worker-01",
                "zone": "us-central1-b",
                "status": "RUNNING",
                "machineType": "e2-standard-4",
                "creationTimestamp": "2026-03-24T12:00:00Z",
                "networkInterfaces": [
                    {
                        "network": "core-vpc",
                        "networkIP": "10.10.4.12",
                        "accessConfigs": [
                            {"name": "nat-access", "natIP": "34.120.50.80", "type": "ONE_TO_ONE_NAT"}
                        ]
                    }
                ],
                "labels": {"env": "prod"}
            }
        ]"""

        def mock_runner(args, timeout, env=None):
            return subprocess.CompletedProcess(args, 0, stdout=mock_payload, stderr="")

        client = GcloudClient(runner=mock_runner)
        instances = client.list_instances(filter_expr="status=RUNNING")

        self.assertEqual(len(instances), 1)
        inst = instances[0]
        self.assertEqual(inst.id, "2001")
        self.assertEqual(inst.name, "api-worker-01")
        self.assertEqual(inst.status, "RUNNING")
        self.assertEqual(inst.labels.get("env"), "prod")
        self.assertEqual(len(inst.network_interfaces), 1)
        self.assertEqual(inst.network_interfaces[0].network_ip, "10.10.4.12")
        self.assertEqual(
            inst.network_interfaces[0].access_configs[0].nat_ip, "34.120.50.80"
        )

    def test_run_command_error(self) -> None:
        def mock_runner(args, timeout, env=None):
            return subprocess.CompletedProcess(
                args,
                1,
                stdout="",
                stderr="ERROR: (gcloud.compute.instances.create) Zone [us-central1-x] not found.",
            )

        client = GcloudClient(runner=mock_runner)
        with self.assertRaises(GcloudCommandError) as ctx:
            client.run_raw(["compute", "instances", "create", "test-vm"])

        self.assertEqual(ctx.exception.exit_code, 1)
        self.assertIn("Zone [us-central1-x] not found", ctx.exception.stderr)

    def test_timeout_error(self) -> None:
        def mock_runner(args, timeout, env=None):
            raise subprocess.TimeoutExpired(args, timeout)

        client = GcloudClient(runner=mock_runner)
        with self.assertRaises(GcloudTimeoutError):
            client.run_raw(["storage", "buckets", "list"])


if __name__ == "__main__":
    unittest.main()
