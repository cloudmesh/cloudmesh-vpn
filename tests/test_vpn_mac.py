import pytest
from unittest.mock import MagicMock, patch, call
from cloudmesh.vpn.vpn import Vpn
from cloudmesh.vpn.strategies.mac_openconnect_keychain import MacOpenConnectKeychainStrategy
from cloudmesh.vpn.strategies.mac_openconnect_decrypted import MacOpenConnectDecryptedStrategy
from cloudmesh.vpn.strategies.mac_openconnect_pw import MacOpenConnectPwStrategy

class TestVpnMac:
    """Tests for VPN functionality on macOS."""

    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=True)
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    def test_provider_selection(self, mock_linux, mock_win, mock_mac):
        """Test that the correct strategy is selected based on the provider."""
        
        # Test default provider
        vpn_default = Vpn()
        assert isinstance(vpn_default.strategy, MacOpenConnectDecryptedStrategy)

        # Test openconnect-keychain
        vpn_keychain = Vpn(provider="openconnect-keychain")
        assert isinstance(vpn_keychain.strategy, MacOpenConnectKeychainStrategy)

        # Test openconnect-pw
        vpn_pw = Vpn(provider="openconnect-pw")
        assert isinstance(vpn_pw.strategy, MacOpenConnectPwStrategy)

        # Test deprecated cisco provider
        with pytest.raises(ValueError, match="The 'cisco' provider is deprecated"):
            Vpn(provider="cisco")

    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=True)
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("subprocess.check_output")
    def test_keychain_strategy_lookup_success(self, mock_output, mock_linux, mock_win, mock_mac):
        """Test successful passphrase retrieval from Keychain."""
        mock_output.return_value = "my-secret-passphrase\n"
        
        vpn = Vpn(provider="openconnect-keychain")
        strategy = vpn.strategy
        
        # Mock credentials
        creds = {"cert_path": "/tmp/cert", "key_path": "/tmp/key"}
        
        # We only want to test the lookup part, so we mock the rest of connect
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            # Mock psutil to simulate process start
            with patch("psutil.process_iter") as mock_iter:
                mock_proc = MagicMock()
                mock_proc.info = {"name": "openconnect", "pid": 1234}
                mock_iter.return_value = [mock_proc]
                
                result = strategy.connect(creds, "uva", no_split=True)
                assert result is True
                
        # Verify the security command was called correctly
        mock_output.assert_called_with(
            ["security", "find-generic-password", "-w", "-a", "uva", "-s", "uva-key-pass"],
            text=True,
            stderr=subprocess.STDOUT
        )

    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=True)
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("subprocess.check_output")
    def test_keychain_strategy_lookup_failure(self, mock_output, mock_linux, mock_win, mock_mac):
        """Test failure when passphrase is missing from Keychain."""
        import subprocess
        mock_output.side_effect = subprocess.CalledProcessError(1, "cmd", output="item not found")
        
        vpn = Vpn(provider="openconnect-keychain")
        creds = {"cert_path": "/tmp/cert", "key_path": "/tmp/key"}
        
        result = vpn.strategy.connect(creds, "uva", no_split=True)
        assert result is False

    @patch("cloudmesh.vpn.vpn.os_is_mac", return_value=True)
    @patch("cloudmesh.vpn.vpn.os_is_windows", return_value=False)
    @patch("cloudmesh.vpn.vpn.os_is_linux", return_value=False)
    @patch("psutil.process_iter")
    @patch("subprocess.check_output")
    def test_watch_logic(self, mock_output, mock_iter, mock_linux, mock_win, mock_mac):
        """Test the watch() method for detecting VPN state."""
        vpn = Vpn()
        strategy = vpn.strategy
        
        # Scenario 1: Everything is running
        mock_proc_openconnect = MagicMock()
        mock_proc_openconnect.info = {"name": "openconnect", "pid": 100}
        mock_proc_slice = MagicMock()
        mock_proc_slice.info = {"name": "vpn-slice", "pid": 101}
        mock_iter.return_value = [mock_proc_openconnect, mock_proc_slice]
        
        # Mock netstat output to show a route
        mock_output.return_value = "Destination Gateway Flags Vi Interface\n128.143.0.0  192.168.1.1  UGS  10  utun1"
        
        evidence = strategy.watch()
        
        assert any("openconnect" in e and "running" in e for e in evidence)
        assert any("vpn-slice" in e and "running" in e for e in evidence)
        assert any("Route to 128.143.0.0/16 found" in e for e in evidence)

        # Scenario 2: Nothing is running
        mock_iter.return_value = []
        evidence = strategy.watch()
        assert any("openconnect" in e and "NOT running" in e for e in evidence)
        assert any("vpn-slice" in e and "NOT running" in e for e in evidence)