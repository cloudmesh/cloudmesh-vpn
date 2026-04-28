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

    @patch("cloudmesh.vpn.vpn.Vpn._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_windows")
    def test_init_windows(self, mock_win, mock_linux, mock_mac, mock_discover):
        """Test initialization on Windows."""
        mock_win.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if "vpncli" in name else None
        vpn_win = Vpn()
        assert "vpncli.exe" in vpn_win.anyconnect

    @patch("cloudmesh.vpn.vpn.Vpn._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_mac")
    def test_init_mac(self, mock_mac, mock_linux, mock_win, mock_discover):
        """Test initialization on Mac."""
        mock_mac.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if name == "vpn" else None
        vpn_mac = Vpn()
        assert vpn_mac.anyconnect == "/opt/cisco/secureclient/bin/vpn"

    @patch("cloudmesh.vpn.vpn.Vpn._discover_binary")
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux")
    def test_init_linux(self, mock_linux, mock_mac, mock_win, mock_discover):
        """Test initialization on Linux."""
        mock_linux.return_value = True
        mock_discover.side_effect = lambda name, paths: paths[0] if name == "vpn" else None
        vpn_linux = Vpn()
        assert vpn_linux.anyconnect == "/opt/cisco/anyconnect/bin/vpn"

    def test_is_user_auth(self, vpn):
        """Test is_user_auth method."""
        # ufl requires user auth
        assert vpn.is_user_auth("ufl") is True
        # uva does not require user auth (auth: cert)
        assert vpn.is_user_auth("uva") is False

    @patch("os.path.exists")
    @patch("os.path.isfile")
    def test_is_docker(self, mock_isfile, mock_exists, vpn):
        """Test is_docker method."""
        # Simulate docker environment
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        with patch("builtins.open", pytest.raises(Exception)): # avoid actual open
            pass
        
        # We need to mock the open() call inside is_docker
        with patch("builtins.open", MagicMock(return_value=["docker"])):
            assert vpn.is_docker() is True

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
    def test_enabled_windows(self, mock_proc, mock_win, vpn):
        """Test enabled() on Windows checking for openconnect process."""
        mock_win.return_value = True
        
        # Mock process list to include openconnect.exe
        mock_process = MagicMock()
        mock_process.info = {"name": "openconnect.exe"}
        mock_proc.return_value = [mock_process]
        
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