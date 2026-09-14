"""Shared backend entry points for TMS data imports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frappe
from frappe import _
from frappe.utils.file_manager import get_file_path

from transport_management.imports import location_importer, material_importer, owned_truck_importer


IMPORT_TYPE_TRANSPORT_LOCATIONS = "Transport Locations"
IMPORT_TYPE_OWNED_TRUCKS = "Owned Trucks"
IMPORT_TYPE_MATERIALS = "Materials"
ALLOWED_EXTENSIONS = {".xlsx", ".csv"}


def get_supported_import_types() -> list[dict[str, str]]:
	return [
		{
			"value": IMPORT_TYPE_TRANSPORT_LOCATIONS,
			"label": _("Transport Locations"),
			"description": _("Import loading and unloading locations from a workbook."),
		},
		{
			"value": IMPORT_TYPE_OWNED_TRUCKS,
			"label": _("Owned Trucks"),
			"description": _("Import owned Truck records from a structured vehicle list."),
		},
		{
			"value": IMPORT_TYPE_MATERIALS,
			"label": _("Materials"),
			"description": _("Import operational Materials and allowed Truck Types."),
		}
	]


def require_import_manager() -> None:
	frappe.only_for("System Manager")


def validate_import_type(import_type: str) -> None:
	if import_type not in {IMPORT_TYPE_TRANSPORT_LOCATIONS, IMPORT_TYPE_OWNED_TRUCKS, IMPORT_TYPE_MATERIALS}:
		frappe.throw(_("Unsupported import type: {0}").format(frappe.bold(import_type)))


def get_uploaded_file_path(file_name: str) -> tuple[str, str]:
	if not file_name:
		frappe.throw(_("Please upload a file before running import."))

	file_doc = frappe.get_doc("File", file_name)
	file_doc.check_permission("read")

	extension = Path(file_doc.file_name or file_doc.file_url or "").suffix.lower()
	if extension not in ALLOWED_EXTENSIONS:
		frappe.throw(
			_("Only {0} files are supported.").format(
				", ".join(sorted(ALLOWED_EXTENSIONS))
			)
		)

	return file_doc.file_name, get_file_path(file_doc.name)


def build_import_response(
	*,
	import_type: str,
	file_name: str,
	result: dict[str, Any],
) -> dict[str, Any]:
	return {
		"import_type": import_type,
		"file_name": file_name,
		"summary": result["summary"],
		"records": result["records"],
		"invalid_rows": result["invalid_rows"],
	}


@frappe.whitelist()
def get_import_options() -> dict[str, Any]:
	require_import_manager()
	return {"import_types": get_supported_import_types(), "allowed_extensions": sorted(ALLOWED_EXTENSIONS)}


@frappe.whitelist()
def dry_run_import(import_type: str, file_name: str) -> dict[str, Any]:
	require_import_manager()
	validate_import_type(import_type)
	display_name, file_path = get_uploaded_file_path(file_name)
	result = get_importer(import_type)["dry_run"](file_path)
	return build_import_response(import_type=import_type, file_name=display_name, result=result)


@frappe.whitelist()
def run_import(import_type: str, file_name: str) -> dict[str, Any]:
	require_import_manager()
	validate_import_type(import_type)
	display_name, file_path = get_uploaded_file_path(file_name)
	result = get_importer(import_type)["import"](file_path)
	create_import_log(import_type=import_type, file_name=file_name, display_name=display_name, result=result)
	return build_import_response(import_type=import_type, file_name=display_name, result=result)


def get_importer(import_type: str) -> dict[str, Any]:
	if import_type == IMPORT_TYPE_TRANSPORT_LOCATIONS:
		return {
			"dry_run": location_importer.dry_run_location_import,
			"import": location_importer.import_new_locations,
		}
	if import_type == IMPORT_TYPE_OWNED_TRUCKS:
		return {
			"dry_run": owned_truck_importer.dry_run_owned_truck_import,
			"import": owned_truck_importer.import_new_owned_trucks,
		}
	if import_type == IMPORT_TYPE_MATERIALS:
		return {
			"dry_run": material_importer.dry_run_material_import,
			"import": material_importer.import_new_materials,
		}
	frappe.throw(_("Unsupported import type: {0}").format(frappe.bold(import_type)))


def create_import_log(
	*,
	import_type: str,
	file_name: str,
	display_name: str,
	result: dict[str, Any],
) -> None:
	summary = result["summary"]
	conflict_count = summary.get("conflicts", summary.get("conflict", 0))
	status = "Completed" if summary["failed"] == 0 else "Partial"
	if conflict_count:
		status = "Failed"

	log = frappe.new_doc("TMS Import Log")
	log.import_type = import_type
	log.source_file = file_name
	log.filename = display_name
	log.source_rows = summary["source_rows"]
	log.created_count = summary["created"]
	log.skipped_count = summary["skipped"]
	log.failed_count = summary["failed"]
	log.status = status
	log.insert()
