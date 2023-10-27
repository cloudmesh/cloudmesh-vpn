# Documentation: https://docs.brew.sh/Formula-Cookbook
#                https://rubydoc.brew.sh/Formula
# PLEASE REMOVE ALL GENERATED COMMENTS BEFORE SUBMITTING YOUR PULL REQUEST!
cask "cisco-secure-client" do
  version "5.0.01242"
  desc "cisco client"
  homepage "https://www.cisco.com/site/us/en/products/security/secure-client/index.html"
  url "https://olemiss.edu/helpdesk/vpn/_files/cisco-secure-client-macos-5.0.01242-predeploy-k9.dmg"
  sha256 "54ce96a427efad22c755332f6b56fc3559e811a3add15cb3485e5e409bb20aaf"

  pkg "Cisco Secure Client.pkg"

  uninstall pkgutil: [

          ],
          delete:  [
              "/Applications/Cisco/Cisco Secure Client.app",
          ]
  # depends_on "cmake" => :build


end
