"""mcp_server.py - exposes Meridian's seven core tools over MCP.

Rule: the server decides permissions, not the model. Each tool may write only
to its own layer; the rule is enforced inside write_table() in lib/io.py.
"""
import os
from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP   # official MCP Python SDK: pip install mcp

import ch07_profiling.profile_source as profile_source
import ch08_ingestion.ingest_to_bronze as ingest_to_bronze
import ch09_medallion.clean_silver as clean_silver
import ch10_quality.quality_checks as quality_checks
import ch11_modeling.model_checks as model_checks
import ch13_operations.check_pipeline_logs as check_pipeline_logs
import ch14_governance.extract_metadata as extract_metadata

WRITE_SCOPE = {            # tool name -> where it may write
    "profil":    ["reports/", "contracts/"],
    "yukleme":   ["bronze"],
    "temizlik":  ["silver"],
    "kalite":    ["quality"],
    "modelleme": [],
    "ariza":     ["ch13_operations/incident_log.yaml"],
    "katalog":   ["metadata/"],
}

mcp = FastMCP("meridian-tools")


@contextmanager
def guarded(tool):
    """Puts the tool's write scope into an environment variable while it runs."""
    os.environ["MERIDIAN_WRITE_SCOPE"] = ",".join(WRITE_SCOPE[tool])
    os.environ["MERIDIAN_TOOL"] = tool
    try:
        yield
    finally:
        os.environ.pop("MERIDIAN_WRITE_SCOPE", None)
        os.environ.pop("MERIDIAN_TOOL", None)


@mcp.tool()
def profil(path: str, table: str = "", guide: str = "ref/source_guide.yaml") -> dict:
    """Profiles a source file before ingestion. Read-only."""
    with guarded("profil"):
        return profile_source.run(path, table or None, guide)


@mcp.tool()
def yukleme(source: str, since: str = "", until: str = "") -> dict:
    """Loads one source into bronze (source: mm_pos | bazaarly_dump | bz_tickets | fx). Writes only to bronze."""
    dates = {k: v for k, v in {"since": since, "until": until}.items() if v}
    with guarded("yukleme"):
        return ingest_to_bronze.run(source=source, **dates)


@mcp.tool()
def temizlik(size: str = "small") -> dict:
    """Rebuilds silver tables from bronze (size: small | large). Writes only to silver."""
    with guarded("temizlik"):
        return clean_silver.run(size=size)


@mcp.tool()
def kalite(rules: str = "ch10_quality/rules.yaml") -> dict:
    """Runs data quality rules. Writes only to the quality schema."""
    with guarded("kalite"):
        return quality_checks.run(rules_path=rules)


@mcp.tool()
def modelleme() -> dict:
    """Tests grain, keys and cardinality of the gold model. Read-only."""
    with guarded("modelleme"):
        return model_checks.run()


@mcp.tool()
def ariza(log_date: str) -> dict:
    """Scans pipeline logs for a date (YYYY-MM-DD) and drafts an incident. Appends to incident log only."""
    with guarded("ariza"):
        return check_pipeline_logs.run(f"data/raw/ops/pipeline_logs/{log_date}.log")


@mcp.tool()
def katalog(tables: list[str]) -> dict:
    """Extracts metadata for tables. Writes only under metadata/."""
    with guarded("katalog"):
        return extract_metadata.run(tables=tables)


if __name__ == "__main__":
    mcp.run()
