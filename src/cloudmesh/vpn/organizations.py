import os
import yaml
from typing import Any, Dict
from importlib import resources

def get_organizations() -> Dict[str, Any]:
    """Load and validate VPN Organization Configurations from YAML."""
    if not hasattr(get_organizations, "_cache"):
        user_config = os.path.expanduser("~/cloudmesh/vpn/vpn.yaml")
        if os.path.exists(user_config):
            with open(user_config, "r") as f:
                data = yaml.safe_load(f)
        else:
            with resources.files("cloudmesh.vpn").joinpath("organizations.yaml").open("r") as f:
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