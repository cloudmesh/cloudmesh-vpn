from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import os
import requests
from cloudmesh.common.Shell import Console
from cloudmesh.common.util import path_expand

from cloudmesh.vpn.organizations import organizations

class VpnOSStrategy(ABC):
    """Abstract Base Class for OS-specific VPN strategies."""

    def __init__(self, vpn_context: 'Vpn'):
        self.vpn = vpn_context
        self._openconnect = None
        self._anyconnect = None

    @property
    def openconnect(self) -> Optional[str]:
        if self._openconnect is None:
            self._openconnect = self._discover_openconnect()
        return self._openconnect

    @property
    def anyconnect(self) -> Optional[str]:
        if self._anyconnect is None:
            self._anyconnect = self._discover_anyconnect()
        return self._anyconnect

    @abstractmethod
    def _discover_openconnect(self) -> Optional[str]:
        pass

    @abstractmethod
    def _discover_anyconnect(self) -> Optional[str]:
        pass

    @abstractmethod
    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        pass

    @abstractmethod
    def watch(self) -> List[str]:
        """Check for evidence that the VPN is active and using split-routing.
        Returns a list of evidence strings.
        """
        pass

    def get_reset_commands(self, service: Optional[str] = None) -> List[str]:
        """Return a list of shell commands to remove VPN routes."""
        return []

    def reset_routes(self, service: Optional[str] = None) -> bool:
        """Execute the commands to remove VPN routes."""
        return True

    def _verify_certs(self, cert_paths: List[str]) -> bool:
        for path in cert_paths:
            expanded_path = path_expand(path)
            if not os.path.exists(expanded_path):
                Console.error(f"Certificate file not found: {expanded_path}")
                return False
        return True

    def _check_ip_info(self) -> bool:
        """Check if the current public IP belongs to the configured organization."""
        try:
            # Reduced timeout to 2s to prevent CLI lag
            res = requests.get("https://ipinfo.io", timeout=2)
            res.raise_for_status()
            org_info = res.json().get("org", "")
            checks = organizations.get(self.vpn.service_key.lower(), {}).get("connection_check", [])
            return any(check in org_info for check in checks)
        except (requests.RequestException, ValueError):
            return False

    def get_current_org(self) -> Optional[str]:
        """Identify which configured organization is currently connected."""
        try:
            res = requests.get("https://ipinfo.io", timeout=2)
            res.raise_for_status()
            org_info = res.json().get("org", "")
            for org_name, config in organizations.items():
                checks = config.get("connection_check", [])
                if any(check in org_info for check in checks):
                    return org_name
        except (requests.RequestException, ValueError):
            pass
        return None

    def _discover_binary(self, binary_name: str, common_paths: List[str]) -> Optional[str]:
        import shutil
        path = shutil.which(binary_name)
        if path:
            return path
        for p in common_paths:
            if os.path.exists(p) and os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None
