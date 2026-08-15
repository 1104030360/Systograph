from __future__ import annotations

from systograph.core.models.ua_analysis import (
    UaCallRow,
    UaEndpointRow,
    UaResourceRow,
    UaSymbolRow,
    UaWarning,
)
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError
from systograph.core.services.ua_sidecar_script_models import UaStructureFile

SERVICE_KIND = "service"


def project_structure_rows(
    rows: tuple[UaStructureFile, ...],
    approved: dict[str, int],
) -> tuple[
    tuple[UaSymbolRow, ...],
    tuple[UaCallRow, ...],
    tuple[UaResourceRow, ...],
    tuple[UaEndpointRow, ...],
    tuple[UaWarning, ...],
]:
    symbols: list[UaSymbolRow] = []
    calls: list[UaCallRow] = []
    resources: list[UaResourceRow] = []
    endpoints: list[UaEndpointRow] = []
    warnings: list[UaWarning] = []
    for row in rows:
        symbols.extend(_symbols(row, approved))
        calls.extend(_calls(row, approved))
        resources.extend(_resources(row, approved, warnings))
        endpoints.extend(_endpoints(row, approved))
    return (
        tuple(sorted(symbols, key=_symbol_key)),
        tuple(sorted(calls, key=_call_key)),
        tuple(sorted(resources, key=_resource_key)),
        tuple(sorted(endpoints, key=_endpoint_key)),
        tuple(warnings),
    )


def _symbols(
    row: UaStructureFile,
    approved: dict[str, int],
) -> list[UaSymbolRow]:
    items: list[UaSymbolRow] = [
        UaSymbolRow(
            file=row.path,
            name=item.name,
            kind="function",
            line_start=item.start_line,
            line_end=item.end_line,
        )
        for item in row.functions
    ]
    items.extend(
        UaSymbolRow(
            file=row.path,
            name=item.name,
            kind="class",
            line_start=item.start_line,
            line_end=item.end_line,
        )
        for item in row.classes
    )
    items.extend(
        UaSymbolRow(
            file=row.path,
            name=item.name,
            kind="export",
            line_start=item.line,
            line_end=item.line,
        )
        for item in row.exports
    )
    for item in items:
        _validate_span(item.file, item.line_start, item.line_end, approved)
    return items


def _calls(
    row: UaStructureFile,
    approved: dict[str, int],
) -> list[UaCallRow]:
    items = [
        UaCallRow(
            file=row.path,
            caller=item.caller,
            callee=item.callee,
            line_number=item.line_number,
        )
        for item in row.call_graph
    ]
    for item in items:
        _validate_span(item.file, item.line_number, item.line_number, approved)
    return items


def _resources(
    row: UaStructureFile,
    approved: dict[str, int],
    warnings: list[UaWarning],
) -> list[UaResourceRow]:
    items = [
        UaResourceRow(
            file=row.path,
            name=item.name,
            kind=item.kind,
            line_start=item.start_line,
            line_end=item.end_line,
        )
        for item in row.resources
    ]
    items.extend(
        UaResourceRow(
            file=row.path,
            name=item.name,
            kind=SERVICE_KIND,
            line_start=item.start_line,
            line_end=_clamped_service_end(
                row.path, item.end_line, approved, warnings
            ),
        )
        for item in row.services
    )
    for item in items:
        _validate_span(item.file, item.line_start, item.line_end, approved)
    return items


def _clamped_service_end(
    file: str,
    end: int | None,
    approved: dict[str, int],
    warnings: list[UaWarning],
) -> int | None:
    # The upstream Dockerfile parser reports the last stage of a
    # trailing-newline file one line past EOF; only that exact signature
    # is corrected, and never silently.
    maximum = approved[file]
    if end is None or maximum <= 0 or end != maximum + 1:
        return end
    warnings.append(
        UaWarning(
            stage="structure_projection",
            message=(
                f"service end line clamped to file bounds: "
                f"{file} {end} -> {maximum}"
            ),
        )
    )
    return maximum


def _endpoints(
    row: UaStructureFile,
    approved: dict[str, int],
) -> list[UaEndpointRow]:
    items: list[UaEndpointRow] = []
    for item in row.endpoints:
        start = item.line or item.start_line
        end = item.line or item.end_line or start
        result = UaEndpointRow(
            file=row.path,
            method=item.method,
            path=item.path,
            line_start=start,
            line_end=end,
        )
        _validate_span(result.file, start, end, approved)
        items.append(result)
    return items


def _validate_span(
    file: str,
    start: int | None,
    end: int | None,
    approved: dict[str, int],
) -> None:
    if start is None and end is None:
        return
    if start is None or end is None or end < start:
        raise UaAnalysisError("ua_line_invalid", "UA line range is invalid")
    maximum = approved[file]
    if maximum > 0 and end > maximum:
        raise UaAnalysisError(
            "ua_line_invalid",
            "UA line range exceeds approved file bounds",
        )


def _symbol_key(item: UaSymbolRow) -> tuple[str, int, str, str]:
    return (item.file, item.line_start, item.kind, item.name)


def _call_key(item: UaCallRow) -> tuple[str, int, str, str]:
    return (item.file, item.line_number, item.caller, item.callee)


def _resource_key(item: UaResourceRow) -> tuple[str, int, str, str]:
    return (item.file, item.line_start or 0, item.kind, item.name)


def _endpoint_key(item: UaEndpointRow) -> tuple[str, int, str, str]:
    return (item.file, item.line_start or 0, item.method or "", item.path)
