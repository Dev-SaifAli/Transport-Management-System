#!/usr/bin/env python
"""Invalidate Frappe's shared assets manifest cache for Railway web startup."""

from __future__ import annotations

import os
import sys
import time
import traceback


def main() -> int:
	site = os.environ.get("FRAPPE_SITE")
	sites_path = os.environ.get("SITES_PATH", "/home/frappe/frappe-bench/sites")
	bench_root = os.environ.get("FRAPPE_BENCH_ROOT", "/home/frappe/frappe-bench")
	attempts = int(os.environ.get("RAILWAY_ASSET_CACHE_CLEAR_ATTEMPTS", "6"))
	delay = float(os.environ.get("RAILWAY_ASSET_CACHE_CLEAR_RETRY_SECONDS", "2"))

	if not site:
		print("[railway] FRAPPE_SITE is required before invalidating assets_json cache", file=sys.stderr)
		return 1

	os.chdir(bench_root)

	import frappe

	for attempt in range(1, attempts + 1):
		try:
			frappe.init(site=site, sites_path=sites_path)
			frappe.client_cache.delete_value("assets_json", shared=True)
			print("[railway] Invalidated Frappe shared assets_json cache", flush=True)
			return 0
		except Exception:
			if attempt >= attempts:
				print("[railway] Failed to invalidate Frappe shared assets_json cache", file=sys.stderr)
				traceback.print_exc()
				return 1
			print(
				f"[railway] assets_json cache invalidation failed; retrying ({attempt}/{attempts})",
				file=sys.stderr,
				flush=True,
			)
			time.sleep(delay)
		finally:
			frappe.destroy()

	return 1


if __name__ == "__main__":
	raise SystemExit(main())
