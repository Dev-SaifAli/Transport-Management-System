"""Apply the single TMS workspace visibility rules to existing installations."""

from transport_management.patches.setup_al_rana_native_ux import execute as configure_native_ux


def execute():
	configure_native_ux()
