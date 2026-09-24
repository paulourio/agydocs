"""
Production-grade programmatic client wrapper for the Google Cloud CLI (gcloud).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class GcloudError(Exception):
    """Base exception for all gcloud client errors."""


class GcloudCommandError(GcloudError):
    """Raised when gcloud terminates with a non-zero exit code."""

    def __init__(self, exit_code: int, stderr: str, command: list[str]) -> None:
        super().__init__(f"gcloud command failed (exit {exit_code}): {stderr.strip()}")
        self.exit_code = exit_code
        self.stderr = stderr
        self.command = command


class GcloudTimeoutError(GcloudError):
    """Raised when a gcloud command execution exceeds the configured timeout."""


@dataclass(frozen=True)
class AccessConfig:
    name: str
    nat_ip: str
    type: str = "ONE_TO_ONE_NAT"


@dataclass(frozen=True)
class NetworkInterface:
    network: str
    network_ip: str
    access_configs: list[AccessConfig] = field(default_factory=list)


@dataclass(frozen=True)
class ComputeInstance:
    id: str
    name: str
    zone: str
    status: str
    machine_type: str
    creation_timestamp: str
    network_interfaces: list[NetworkInterface] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StorageBucket:
    name: str
    location: str
    storage_class: str
    time_created: str


def default_runner(
    args: list[str],
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Default process runner using subprocess.run with argument vector isolation."""
    run_env = os.environ.copy()
    run_env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    if env:
        run_env.update(env)

    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        env=run_env,
        check=False,
    )


class GcloudClient:
    """Provides a typed Python interface to Google Cloud CLI operations."""

    def __init__(
        self,
        project: str | None = None,
        impersonate_service_account: str | None = None,
        configuration: str | None = None,
        binary_path: str = "gcloud",
        default_timeout: float = 30.0,
        runner: Callable[..., subprocess.CompletedProcess[str]] = default_runner,
    ) -> None:
        self.project = project
        self.impersonate_service_account = impersonate_service_account
        self.configuration = configuration
        self.binary_path = binary_path
        self.default_timeout = default_timeout
        self.runner = runner

    def build_args(
        self, subcommand_args: list[str], format_spec: str | None = None
    ) -> list[str]:
        """Compiles base global flags alongside command-specific arguments."""
        args = [self.binary_path]
        args.extend(subcommand_args)

        if self.project:
            args.append(f"--project={self.project}")
        if self.impersonate_service_account:
            args.append(
                f"--impersonate-service-account={self.impersonate_service_account}"
            )
        if self.configuration:
            args.append(f"--configuration={self.configuration}")

        args.append("--quiet")
        if format_spec:
            args.append(f"--format={format_spec}")

        return args

    def run_raw(
        self,
        subcommand_args: list[str],
        format_spec: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Executes a gcloud command and returns standard output."""
        if not subcommand_args:
            raise ValueError("subcommand_args cannot be empty")

        cmd = self.build_args(subcommand_args, format_spec)
        t = timeout if timeout is not None else self.default_timeout

        try:
            res = self.runner(cmd, timeout=t)
        except subprocess.TimeoutExpired as exc:
            raise GcloudTimeoutError(
                f"Command timed out after {t} seconds: {' '.join(cmd)}"
            ) from exc

        if res.returncode != 0:
            raise GcloudCommandError(res.returncode, res.stderr, cmd)

        return res.stdout

    def run_json(self, subcommand_args: list[str], timeout: float | None = None) -> Any:
        """Executes a gcloud command requesting JSON output and parses the result."""
        raw_stdout = self.run_raw(subcommand_args, format_spec="json", timeout=timeout)
        if not raw_stdout.strip():
            return None
        return json.loads(raw_stdout)

    def list_instances(self, filter_expr: str | None = None) -> list[ComputeInstance]:
        """Lists Compute Engine instances and maps them into typed data structures."""
        sub = ["compute", "instances", "list"]
        if filter_expr:
            sub.append(f"--filter={filter_expr}")

        data = self.run_json(sub)
        if not data:
            return []

        results: list[ComputeInstance] = []
        for item in data:
            interfaces: list[NetworkInterface] = []
            for iface in item.get("networkInterfaces", []):
                configs: list[AccessConfig] = []
                for ac in iface.get("accessConfigs", []):
                    configs.append(
                        AccessConfig(
                            name=ac.get("name", ""),
                            nat_ip=ac.get("natIP", ""),
                            type=ac.get("type", "ONE_TO_ONE_NAT"),
                        )
                    )
                interfaces.append(
                    NetworkInterface(
                        network=iface.get("network", ""),
                        network_ip=iface.get("networkIP", ""),
                        access_configs=configs,
                    )
                )

            results.append(
                ComputeInstance(
                    id=str(item.get("id", "")),
                    name=item.get("name", ""),
                    zone=item.get("zone", ""),
                    status=item.get("status", ""),
                    machine_type=item.get("machineType", ""),
                    creation_timestamp=item.get("creationTimestamp", ""),
                    network_interfaces=interfaces,
                    labels=item.get("labels", {}),
                )
            )
        return results

    @staticmethod
    def build_filter(terms: dict[str, str]) -> str:
        """Compiles a safe boolean filter expression from key-value pairs."""
        if not terms:
            return ""
        parts: list[str] = []
        for k, v in terms.items():
            if "*" in v:
                parts.append(f"{k}:{v}")
            else:
                parts.append(f"{k}={v}")
        return " AND ".join(parts)
