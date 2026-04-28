import pytest
from unittest.mock import MagicMock, patch
from cloudmesh.vpn.vpn import Vpn

class TestVpn:
    """Tests for the Vpn class."""

    @pytest.fixture
    def vpn(self):
        """Fixture to provide a Vpn instance."""
        return Vpn(service="uva")

    def test_init(self, vpn):
        """Test initialization of Vpn object."""
        assert vpn.service_key == "uva"
        assert vpn.service == "UVA Anywhere"
        assert vpn.timeout == 60

    @patch("cloudmesh.vpn.vpn.WindowsVpnStrategy._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_windows")
    def test_init_windows(self, mock_win, mock_linux, mock_mac, mock_discover):
        """Test initialization on Windows."""
        mock_win.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if "vpncli" in name else None
        vpn_win = Vpn()
        assert "vpncli.exe" in vpn_win.strategy.anyconnect

    @patch("cloudmesh.vpn.vpn.MacVpnStrategy._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_mac")
    def test_init_mac(self, mock_mac, mock_linux, mock_win, mock_discover):
        """Test initialization on Mac."""
        mock_mac.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if name == "vpn" else None
        vpn_mac = Vpn()
        assert vpn_mac.strategy.anyconnect == "/opt/cisco/secureclient/bin/vpn"

    @patch("cloudmesh.vpn.vpn.LinuxVpnStrategy._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux")
    def test_init_linux(self, mock_linux, mock_mac, mock_win, mock_discover):
        """Test initialization on Linux."""
        mock_linux.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if name == "vpn" else None
        vpn_linux = Vpn()
        assert vpn_linux.strategy.anyconnect == "/opt/cisco/anyconnect/bin/vpn"

    def test_is_user_auth(self, vpn):
        """Test is_user_auth method."""
        # ufl requires user auth
        assert vpn.is_user_auth("ufl") is True
        # uva does not require user auth (auth: cert)
        assert vpn.is_user_auth("uva") is False

    # test_is_docker removed as is_docker is now internal to LinuxVpnStrategy

    @patch("cloudmesh.vpn.vpn.os_is_mac")
    @patch("requests.get")
    def test_enabled_mac_connected(self, mock_get, mock_mac, vpn):
        """Test enabled() on Mac when connected (via IP check)."""
        mock_mac.return_value = True
        
        # Mock ipinfo.io response
        mock_response = MagicMock()
        mock_response.json.return_value = {"org": "University of Virginia"}
        mock_get.return_value = mock_response
        
        assert vpn.enabled() is True

    @patch("cloudmesh.vpn.vpn.os_is_mac")
    @patch("requests.get")
    def test_enabled_mac_disconnected(self, mock_get, mock_mac, vpn):
        """Test enabled() on Mac when disconnected."""
        mock_mac.return_value = True
        
        # Mock ipinfo.io response with different org
        mock_response = MagicMock()
        mock_response.json.return_value = {"org": "Some Other Org"}
        mock_get.return_value = mock_response
        
        assert vpn.enabled() is False

    @patch("cloudmesh.vpn.vpn.os_is_windows")
    @patch("psutil.process_iter")
    def test_enabled_windows(self, mock_proc, mock_win):
        """Test enabled() on Windows checking for openconnect process."""
        mock_win.return_value = True
        
        # Mock process list to include openconnect.exe
        mock_process = MagicMock()
        mock_process.info = {"name": "openconnect.exe"}
        mock_proc.return_value = [mock_process]
        
        vpn = Vpn()
        assert vpn.enabled() is True

    @patch("cloudmesh.vpn.vpn.os_is_linux")
    @patch("requests.get")
    def test_enabled_linux(self, mock_get, mock_linux, vpn):
        """Test enabled() on Linux."""
        mock_linux.return_value = True
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"org": "University of Virginia"}
        mock_get.return_value = mock_response
        
        assert vpn.enabled() is True