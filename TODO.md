# TODO List for cloudmesh-vpn 6.1.0

## High Priority
- [ ] __Connection Profiles:__ Allow users to save multiple profiles (e.g., different services, different certificate sets) and switch between them using a simple flag like `--profile=work` or `--profile=school`.
- [ ] __System Tray/Menu Bar Integration:__ For macOS and Windows, a small icon in the tray that shows connection status (Green/Red) and allows a right-click to connect/disconnect.
- [ ] __Certificate Expiry Alerts:__ Add a check that reads the certificate files and warns the user via the CLI if their certificates are expiring within the next 30 days.
- [ ] __Multi-Factor Authentication (MFA) Support:__ Improve the handling of interactive MFA prompts (like Duo or Microsoft Authenticator) to make the CLI experience smoother.
