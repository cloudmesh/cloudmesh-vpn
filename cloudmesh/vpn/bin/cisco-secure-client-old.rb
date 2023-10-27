cask "cisco-secure-client" do
  version "5.0.01242"
  sha256 "504A43CD4777F73AEC2AC09E184E1AE3"

  url "https://olemiss.edu/helpdesk/vpn/_files/cisco-secure-client-macos-5.0.01242-predeploy-k9.dmg"
  name "Cisco Secure Client"
  desc "Cisco's client to connect to industry and organizational VPNs"
  homepage "https://www.cisco.com/site/us/en/products/security/secure-client/index.html"

  app "vpncli.app"
end
