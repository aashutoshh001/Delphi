"""Workday-backed EmployeeRepository — a NEW door alongside the in-memory one.

Boundary respected: this returns only an EmployeeDataLandscape (which attributes
*exist* and their coverage), NEVER employee rows. It lets the Hypothesis Agent's
LLM know that Workday HRIS data (compensation, tenure, performance, structure)
and the SHL assessment data (UCF / MQ / 360 / HiPo / Leadership) are available,
so it can form feasible hypotheses about them.

Two modes:
  * offline (default): returns a curated, accurate landscape from what we know
    exists in the Workday tenant + SHL assessments. No network — tests/demo stay
    offline and deterministic.
  * live (probe_workday=True and valid Workday creds in the env file): additionally
    confirms the real worker count from Workday's Staffing API and adjusts the
    count/notes accordingly.

Credentials live in a gitignored env file (default: the same hypothesis_agent/.env
that already holds LITELLM_API_KEY), never in code. Required keys for the live
probe: WORKDAY_TENANT_URL, WORKDAY_TENANT_NAME, and either a valid
WORKDAY_BEARER_TOKEN or the four auto-refresh keys (WORKDAY_TOKEN_ENDPOINT,
WORKDAY_REFRESH_TOKEN, WORKDAY_CLIENT_ID, WORKDAY_CLIENT_SECRET).

Verified against the real tenant (cebshl_dpt2): the Staffing v6 /workers endpoint
returns 378 workers; the refresh-token grant works AND rotates the refresh token
on every use — so `_refresh_access_token()` writes the rotated token back to the
env file, otherwise the connection would self-invalidate after one refresh.

Uses only the standard library (urllib) for the probe — no extra dependency; the
offline default needs nothing at all.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from hypothesis_agent.contracts.organization import AttributeField, EmployeeDataLandscape
from hypothesis_agent.logging_setup import get_logger
from hypothesis_agent.ports.employee_repository import EmployeeRepository

logger = get_logger("adapters.workday")

# workday_employee_repository.py -> hypothesis_agent (pkg) -> src -> hypothesis_agent
# (project) -> Delphi (repo root). Same anchor idea used elsewhere; keeps the
# default credential path independent of the process's cwd.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_DEFAULT_ENV_PATH = _REPO_ROOT / "hypothesis_agent" / ".env"

# Live-confirmed: the Workday tenant (cebshl_dpt2) reports this many workers.
_WORKDAY_WORKERS = 378
# SHL assessment coverage across the Workday population (curated estimate).
_ASSESS_COV = 0.94

# Categories are chosen to match the built-in lens `relevant_construct_categories`
# so the relevant lenses actually light up (e.g. compensation_fairness).
_KNOWN_FIELDS: list[AttributeField] = [
    # --- Workday HRIS (row-fetch happens downstream; here we only advertise it) ---
    AttributeField(name="compensation_annual", category="compensation", data_type="numeric",
                   coverage_ratio=1.0, description="Annualized base pay (Workday Core Compensation)."),
    AttributeField(name="tenure_years", category="tenure", data_type="numeric",
                   coverage_ratio=1.0, description="Length of service from Workday hire/service date."),
    AttributeField(name="performance_rating", category="performance", data_type="ordinal",
                   coverage_ratio=0.85, description="Most recent Workday review overall rating."),
    AttributeField(name="job_level", category="role_criticality", data_type="categorical",
                   coverage_ratio=1.0, description="Workday job profile / level."),
    AttributeField(name="supervisory_org", category="manager_ratings", data_type="categorical",
                   coverage_ratio=1.0, description="Reporting structure / manager (Workday)."),
    # --- SHL assessment data (insightsGenieDB / Book1) ---
    AttributeField(name="ucf_skill_scores", category="technical_competency", data_type="ordinal",
                   coverage_ratio=_ASSESS_COV, description="96 UCF skill components (GSA), 0-5."),
    AttributeField(name="ucf_personality_potential", category="behavioural_competency", data_type="categorical",
                   coverage_ratio=_ASSESS_COV, description="20 UCF dimensions (OPQ), Strength/Sufficiency/Weakness."),
    AttributeField(name="leadership_challenges", category="leadership", data_type="numeric",
                   coverage_ratio=_ASSESS_COV, description="27 contextual leadership challenge percentiles (OPQ)."),
    AttributeField(name="enterprise_leadership", category="leadership", data_type="numeric",
                   coverage_ratio=_ASSESS_COV, description="Transactional/Transformational/Network leadership (OPQ+360)."),
    AttributeField(name="hipo_scores", category="leadership", data_type="numeric",
                   coverage_ratio=_ASSESS_COV, description="High-potential Aspiration & Ability (OPQ+MQ)."),
    AttributeField(name="motivation_mq", category="engagement", data_type="numeric",
                   coverage_ratio=0.0, description="18 MQ motivation factors — NOT loaded for this cohort (synthetic only)."),
    AttributeField(name="feedback_360", category="manager_ratings", data_type="numeric",
                   coverage_ratio=0.02, description="360 multi-rater competency ratings — only a small pilot cohort."),
]


class WorkdayEmployeeRepository(EmployeeRepository):
    """Advertises Workday HRIS + SHL assessment data as a schema-level landscape."""

    def __init__(self, env_path: str | Path | None = None, probe_workday: bool = False) -> None:
        self._env_path = Path(env_path) if env_path else _DEFAULT_ENV_PATH
        self._probe = probe_workday

    async def get_data_landscape(self, organization_id: str) -> EmployeeDataLandscape:
        fields = list(_KNOWN_FIELDS)
        count = _WORKDAY_WORKERS
        note = (
            "Workday HRIS (compensation, tenure, performance, structure) + SHL assessments. "
            f"~{_WORKDAY_WORKERS} Workday workers, ~{int(_ASSESS_COV * 100)}% assessed; "
            "MQ not loaded; 360 pilot-only."
        )
        if self._probe:
            live_count, ok = self._probe_workday()
            if ok:
                count = live_count
                note += f" [live Workday probe OK: {live_count} workers]"
            else:
                note += " [live Workday probe failed — count estimated offline]"
        return EmployeeDataLandscape(
            organization_id=organization_id,
            employee_count_estimate=count,
            available_fields=fields,
            notes=note,
        )

    # -- live probe (stdlib only; never raises) ---------------------------------

    def _load_env(self) -> dict[str, str]:
        """Merge the env file (if present) over the process environment, so this
        works whether or not di/container.py already loaded the same .env."""
        env: dict[str, str] = {k: v for k, v in os.environ.items() if k.startswith("WORKDAY_")}
        if self._env_path.exists():
            for line in self._env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line and line.startswith("WORKDAY_"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        return env

    def _persist_refresh_token(self, new_refresh: str) -> None:
        """Workday rotates the refresh token on every use — write the new one
        back so the next run doesn't fail with invalid_grant. Best-effort."""
        try:
            if not self._env_path.exists():
                return
            lines = self._env_path.read_text().splitlines()
            replaced = False
            for i, line in enumerate(lines):
                if line.strip().startswith("WORKDAY_REFRESH_TOKEN="):
                    lines[i] = f"WORKDAY_REFRESH_TOKEN={new_refresh}"
                    replaced = True
                    break
            if not replaced:
                lines.append(f"WORKDAY_REFRESH_TOKEN={new_refresh}")
            self._env_path.write_text("\n".join(lines) + "\n")
            logger.info("persisted rotated Workday refresh token", extra={"extra_fields": {"env_path": str(self._env_path)}})
        except Exception:
            logger.warning("could not persist rotated Workday refresh token")

    def _refresh_access_token(self, env: dict[str, str]) -> str | None:
        endpoint = env.get("WORKDAY_TOKEN_ENDPOINT")
        refresh = env.get("WORKDAY_REFRESH_TOKEN")
        client_id = env.get("WORKDAY_CLIENT_ID")
        client_secret = env.get("WORKDAY_CLIENT_SECRET")
        if not all([endpoint, refresh, client_id, client_secret]):
            return None
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token", "refresh_token": refresh,
            "client_id": client_id, "client_secret": client_secret,
        }).encode()
        req = urllib.request.Request(endpoint, data=data,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                body = json.loads(r.read().decode())
        except Exception:
            return None
        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != refresh:
            self._persist_refresh_token(new_refresh)
        return body.get("access_token")

    def _probe_workday(self) -> tuple[int, bool]:
        """Best-effort live confirmation of worker count. Never raises."""
        try:
            env = self._load_env()
            tenant_url = env.get("WORKDAY_TENANT_URL")
            tenant = env.get("WORKDAY_TENANT_NAME")
            if not tenant_url or not tenant:
                return _WORKDAY_WORKERS, False

            token = env.get("WORKDAY_BEARER_TOKEN")

            def fetch_total(tok: str) -> tuple[int, bool]:
                url = f"{tenant_url.rstrip('/')}/ccx/api/staffing/v6/{tenant}/workers?limit=1&offset=0"
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    return int(json.loads(r.read().decode()).get("total", _WORKDAY_WORKERS)), True

            # Try the existing bearer token first (non-destructive).
            if token:
                try:
                    return fetch_total(token)
                except urllib.error.HTTPError as e:
                    if e.code != 401:
                        raise
                    # expired — fall through to refresh
            # Refresh and retry.
            refreshed = self._refresh_access_token(env)
            if refreshed:
                return fetch_total(refreshed)
        except Exception:
            pass
        return _WORKDAY_WORKERS, False
