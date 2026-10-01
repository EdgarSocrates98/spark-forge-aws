"""Read-only live graph for explicitly declared Glue, Lake Formation and S3 resources."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sparkforge.collect.aws import _offline_hit, _write_and_register
from sparkforge.collect.base import require_boto3
from sparkforge.workspace.manifest import CloudResource, load_manifest

_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")
_CREDENTIAL_ERRORS = {
    "CredentialRetrievalError",
    "ExpiredTokenException",
    "ExpiredToken",
    "InvalidClientTokenId",
    "NoCredentialsError",
    "PartialCredentialsError",
    "UnrecognizedClientException",
}
_ACCESS_ERRORS = {
    "AccessDenied",
    "AccessDeniedException",
    "UnauthorizedException",
}


def workspace_graph_path(workspace: str) -> str:
    name = _SAFE_NAME.sub("_", workspace).strip("._") or "workspace"
    return f".sparkforge/artifacts/workspace_graph/{name}.json"


def collect_workspace_graph(
    manifest_path: str | Path,
    root: Path,
    *,
    now: str,
    max_objects: int = 100,
) -> Any:
    """Collect a bounded graph from only resources declared in ``manifest_path``.

    The collector never discovers tables, buckets or permissions. Missing
    credentials, denied calls and bounded S3 listings remain named in the
    artifact so an unresolved edge cannot be mistaken for an absent edge.
    """

    manifest = load_manifest(manifest_path)
    rel_path = workspace_graph_path(manifest.name)
    hit = _offline_hit(root, rel_path)
    if hit is not None:
        return hit
    if max_objects <= 0:
        raise ValueError("max_objects must be positive")

    boto3 = require_boto3()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    resource_status: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    edge_keys: set[tuple[str, str, str]] = set()
    clients: dict[tuple[str, str, str], Any] = {}

    def add_node(node_id: str, kind: str, **attrs: Any) -> None:
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append({"id": node_id, "kind": kind, "attrs": attrs})

    def add_edge(source: str, relation: str, target: str) -> None:
        key = (source, relation, target)
        if key in edge_keys:
            return
        edge_keys.add(key)
        edges.append({"source": source, "relation": relation, "target": target})

    def add_unresolved(reason: str, resource: CloudResource, **attrs: Any) -> None:
        item = {"reason": reason, "resource_id": resource.id, **attrs}
        unresolved.append(item)

    caller_account, caller_issue = _caller_account(boto3)
    if caller_issue:
        unresolved.append(caller_issue)
    if caller_account:
        add_node(f"account:{caller_account}", "account", account_id=caller_account)

    for resource in manifest.cloud_resources:
        resource_node = f"cloud:{resource.id}"
        add_node(
            resource_node,
            "declared_resource",
            resource_id=resource.id,
            resource_kind=resource.kind,
            services=list(resource.services),
            account_id=resource.account_id,
            region=resource.region,
        )
        if resource.account_id and caller_account:
            target_account_node = f"account:{resource.account_id}"
            add_node(target_account_node, "account", account_id=resource.account_id)
            add_edge(target_account_node, "owns", resource_node)
            if resource.account_id == caller_account:
                add_edge(f"account:{caller_account}", "owns", resource_node)
            elif not resource.role_arn:
                add_unresolved(
                    "cross_account_role_required",
                    resource,
                    caller_account_id=caller_account,
                    target_account_id=resource.account_id,
                )
                resource_status.append(
                    {"resource_id": resource.id, "status": "unresolved", "services": []}
                )
                continue
            else:
                add_edge(resource_node, "cross_account_via", f"role:{resource.role_arn}")
                add_node(f"role:{resource.role_arn}", "iam_role", role_arn=resource.role_arn)
        elif resource.account_id and not caller_account and not resource.role_arn:
            add_unresolved("caller_account_unresolved", resource)
            resource_status.append(
                {"resource_id": resource.id, "status": "unresolved", "services": []}
            )
            continue

        statuses: list[dict[str, Any]] = []
        for service in resource.services:
            try:
                client = client_for(boto3, clients, service, resource)
            except Exception as exc:  # noqa: BLE001 - named AWS outcome
                code = _error_code(exc)
                add_unresolved(_error_reason(exc), resource, service=service, error_code=code)
                statuses.append({"service": service, "status": "unresolved", "error_code": code})
                continue
            if service == "glue":
                statuses.append(
                    _collect_glue(
                        resource,
                        resource_node,
                        client,
                        add_node,
                        add_edge,
                        add_unresolved,
                    )
                )
            elif service == "lakeformation":
                statuses.append(
                    _collect_lakeformation(
                        resource,
                        resource_node,
                        client,
                        add_node,
                        add_edge,
                        add_unresolved,
                    )
                )
            elif service == "s3":
                statuses.append(
                    _collect_s3(
                        resource,
                        resource_node,
                        client,
                        max_objects,
                        add_node,
                        add_edge,
                        add_unresolved,
                    )
                )
        resource_status.append(
            {
                "resource_id": resource.id,
                "status": (
                    "ok" if all(item["status"] == "ok" for item in statuses) else "unresolved"
                ),
                "services": statuses,
            }
        )

    payload = {
        "schema_version": 1,
        "workspace": manifest.name,
        "manifest": str(Path(manifest_path).name),
        "source": "aws:glue,lakeformation,s3",
        "collected_at": now,
        "resources": resource_status,
        "graph": {"nodes": nodes, "edges": edges},
        "unresolved": unresolved,
    }
    content = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return _write_and_register(
        root,
        rel_path,
        content + b"\n",
        kind="workspace_graph",
        source="aws:glue,lakeformation,s3",
        collect_command=(
            "sparkforge collect workspace-graph --repo "
            f"{root} --manifest {manifest_path} --now {now}"
        ),
        now=now,
    )


def _caller_account(boto3: Any) -> tuple[str, dict[str, Any] | None]:
    try:
        response = boto3.client("sts").get_caller_identity()
    except Exception as exc:  # noqa: BLE001 - converted to named evidence
        return "", {"reason": _error_reason(exc), "service": "sts", "error_code": _error_code(exc)}
    account = str(response.get("Account") or "")
    if not account:
        return "", {"reason": "caller_account_unresolved", "service": "sts"}
    return account, None


def client_for(
    boto3: Any,
    clients: dict[tuple[str, str, str], Any],
    service: str,
    resource: CloudResource,
) -> Any:
    key = (service, resource.region, resource.role_arn)
    if key in clients:
        return clients[key]
    kwargs: dict[str, Any] = {}
    if resource.region:
        kwargs["region_name"] = resource.region
    if resource.role_arn:
        credentials = boto3.client("sts", **kwargs).assume_role(
            RoleArn=resource.role_arn,
            RoleSessionName="sparkforge-live-graph",
        )["Credentials"]
        session_kwargs = {
            "aws_access_key_id": credentials["AccessKeyId"],
            "aws_secret_access_key": credentials["SecretAccessKey"],
            "aws_session_token": credentials["SessionToken"],
        }
        if hasattr(boto3, "Session"):
            session = boto3.Session(**session_kwargs)
            client = session.client(service, **kwargs)
        else:
            client = boto3.client(service, **kwargs, **session_kwargs)
    else:
        client = boto3.client(service, **kwargs)
    clients[key] = client
    return client


def _collect_glue(
    resource: CloudResource,
    resource_node: str,
    client: Any,
    add_node: Any,
    add_edge: Any,
    add_unresolved: Any,
) -> dict[str, Any]:
    if not resource.database or not resource.table:
        add_unresolved("glue_resource_declaration_incomplete", resource)
        return {"service": "glue", "status": "unresolved"}
    kwargs: dict[str, Any] = {"DatabaseName": resource.database, "Name": resource.table}
    if resource.catalog_id:
        kwargs["CatalogId"] = resource.catalog_id
    try:
        table = client.get_table(**kwargs).get("Table") or {}
    except Exception as exc:  # noqa: BLE001 - named AWS outcome
        code = _error_code(exc)
        add_unresolved(_error_reason(exc), resource, service="glue", error_code=code)
        return {"service": "glue", "status": "unresolved", "error_code": code}
    table_node = f"glue_table:{resource.id}"
    add_node(
        table_node,
        "glue_table",
        name=str(table.get("Name") or resource.table),
        database=str(table.get("DatabaseName") or resource.database),
        catalog_id=str(table.get("CatalogId") or resource.catalog_id),
        location=str((table.get("StorageDescriptor") or {}).get("Location") or ""),
    )
    add_edge(resource_node, "catalog_contains", table_node)
    return {"service": "glue", "status": "ok"}


def _collect_lakeformation(
    resource: CloudResource,
    resource_node: str,
    client: Any,
    add_node: Any,
    add_edge: Any,
    add_unresolved: Any,
) -> dict[str, Any]:
    if not resource.database or not resource.table:
        add_unresolved("lakeformation_resource_declaration_incomplete", resource)
        return {"service": "lakeformation", "status": "unresolved"}
    table: dict[str, Any] = {"DatabaseName": resource.database, "Name": resource.table}
    if resource.catalog_id:
        table["CatalogId"] = resource.catalog_id
    permissions: list[dict[str, Any]] = []
    permission_error: dict[str, Any] | None = None
    try:
        permission_args: dict[str, Any] = {"Resource": {"Table": table}}
        if resource.catalog_id:
            permission_args["CatalogId"] = resource.catalog_id
        response = client.list_permissions(**permission_args)
        permissions = response.get("PrincipalResourcePermissions") or []
        if response.get("NextToken"):
            add_unresolved(
                "lakeformation_permissions_truncated",
                resource,
                service="lakeformation",
            )
    except Exception as exc:  # noqa: BLE001 - named AWS outcome
        code = _error_code(exc)
        add_unresolved(_error_reason(exc), resource, service="lakeformation", error_code=code)
        permission_error = {"error_code": code}

    settings: dict[str, Any] = {}
    settings_error: dict[str, Any] | None = None
    try:
        settings_args = {"CatalogId": resource.catalog_id} if resource.catalog_id else {}
        settings = client.get_data_lake_settings(**settings_args).get("DataLakeSettings") or {}
    except Exception as exc:  # noqa: BLE001 - named AWS outcome
        code = _error_code(exc)
        add_unresolved(
            _error_reason(exc), resource, service="lakeformation_settings", error_code=code
        )
        settings_error = {"error_code": code}

    lf_node = f"lakeformation:{resource.id}"
    add_node(
        lf_node,
        "lakeformation",
        permission_count=len(permissions),
        settings_status="unresolved" if settings_error else "ok",
        allow_full_table_external_data_access=settings.get("AllowFullTableExternalDataAccess"),
        allow_external_data_filtering=settings.get("AllowExternalDataFiltering"),
    )
    add_edge(resource_node, "governed_by", lf_node)
    for index, grant in enumerate(permissions):
        principal = str((grant.get("Principal") or {}).get("DataLakePrincipalIdentifier") or "")
        if not principal:
            principal = f"grant:{resource.id}:{index}"
        principal_node = f"principal:{principal}"
        add_node(principal_node, "principal", principal=principal)
        add_edge(lf_node, "grants_to", principal_node)
    if permission_error or settings_error:
        errors = permission_error or settings_error or {}
        return {
            "service": "lakeformation",
            "status": "unresolved",
            "permission_count": len(permissions),
            **errors,
        }
    return {
        "service": "lakeformation",
        "status": "unresolved" if response.get("NextToken") else "ok",
        "permission_count": len(permissions),
    }


def _collect_s3(
    resource: CloudResource,
    resource_node: str,
    client: Any,
    max_objects: int,
    add_node: Any,
    add_edge: Any,
    add_unresolved: Any,
) -> dict[str, Any]:
    if not resource.bucket:
        add_unresolved("s3_resource_declaration_incomplete", resource)
        return {"service": "s3", "status": "unresolved"}
    kwargs: dict[str, Any] = {
        "Bucket": resource.bucket,
        "Prefix": resource.prefix,
        "MaxKeys": max_objects,
    }
    try:
        response = client.list_objects_v2(**kwargs)
    except Exception as exc:  # noqa: BLE001 - named AWS outcome
        code = _error_code(exc)
        add_unresolved(_error_reason(exc), resource, service="s3", error_code=code)
        return {"service": "s3", "status": "unresolved", "error_code": code}
    prefix_node = f"s3_prefix:{resource.id}"
    objects = response.get("Contents") or []
    add_node(
        prefix_node,
        "s3_prefix",
        bucket=resource.bucket,
        prefix=resource.prefix,
        object_count=len(objects),
        truncated=bool(response.get("IsTruncated")),
    )
    add_edge(resource_node, "stored_at", prefix_node)
    for item in objects[:max_objects]:
        key = str(item.get("Key") or "")
        if not key:
            continue
        object_node = f"s3_object:{resource.bucket}/{key}"
        add_node(
            object_node,
            "s3_object",
            bucket=resource.bucket,
            key=key,
            size=int(item.get("Size") or 0),
            etag=str(item.get("ETag") or ""),
        )
        add_edge(prefix_node, "contains", object_node)
    if response.get("IsTruncated"):
        add_unresolved(
            "s3_listing_truncated",
            resource,
            service="s3",
            max_objects=max_objects,
        )
    return {
        "service": "s3",
        "status": "unresolved" if response.get("IsTruncated") else "ok",
        "object_count": len(objects),
        "truncated": bool(response.get("IsTruncated")),
    }


def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str((response.get("Error") or {}).get("Code") or "")
    return type(exc).__name__


def _error_reason(exc: BaseException) -> str:
    code = _error_code(exc)
    if type(exc).__name__ in _CREDENTIAL_ERRORS or code in _CREDENTIAL_ERRORS:
        return "credentials_unresolved"
    if code in _ACCESS_ERRORS:
        return "access_denied"
    return "aws_call_failed"


__all__ = ["collect_workspace_graph", "workspace_graph_path"]
