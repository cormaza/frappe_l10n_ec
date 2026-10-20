"""App lifecycle wiring for install, migrate, and uninstall (roadmap Phase 3)."""

from l10n_ec.ecuador_localization.custom_fields import (
	create_sri_custom_fields,
	delete_sri_custom_fields,
)


def after_install() -> None:
	create_sri_custom_fields()


def after_migrate() -> None:
	create_sri_custom_fields()


def before_uninstall() -> None:
	delete_sri_custom_fields()
