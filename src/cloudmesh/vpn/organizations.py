import os
import yaml
from typing import Any, Dict

def get_organizations() -> Dict[str, Any]:
    """Load and validate VPN Organization Configurations from YAML."""
    if not hasattr(get_organizations, "_cache"):
        org_file = os.path.join(os.path.dirname(__file__), "organizations.yaml")
        with open(org_file, "r") as f:
            data = yaml.safe_load(f)
            orgs = data.get("cloudmesh", {}).get("vpn", {})

        # Validate organization configurations
        required_keys = ["host", "connection_check"]
        for org, config in orgs.items():
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(
                    f"Malformed configuration for organization '{org}': "
                    f"Missing required keys: {', '.join(missing_keys)}"
                )
        get_organizations._cache = orgs
    return get_organizations._cache

# Global organizations object
organizations = get_organizations()