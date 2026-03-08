"""Utility for resolving KE description toggle state."""


def resolve_description_usage(ke_id: str, global_toggle: bool, disabled_kes: set) -> bool:
    """Resolve whether description should influence matching for this KE.

    Logic: global ON + KE not in disabled set = use description.

    Args:
        ke_id: Key Event ID (e.g., "KE 55")
        global_toggle: Global use_ke_description toggle from config
        disabled_kes: Set of KE IDs with description explicitly disabled

    Returns:
        True if description should be used for this KE
    """
    if not global_toggle:
        return False
    return ke_id not in disabled_kes
