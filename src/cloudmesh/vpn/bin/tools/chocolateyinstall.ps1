
$ErrorActionPreference = 'Stop';

$url        = 'https://olemiss.edu/helpdesk/vpn/_files/cisco-secure-client-win-5.0.01242-core-vpn-predeploy-k9.msi'
$url64      = 'https://olemiss.edu/helpdesk/vpn/_files/cisco-secure-client-win-5.0.01242-core-vpn-predeploy-k9.msi'

$packageName = 'cisco-secure-client'


$checksum = '0D598CCE56CF6D3272D5E1B1C1266B5F5C816FC367D61D2113EAA41F07D1FC18'
$setupName = $exeToRun

$packageArgs = @{
    packageName   = $env:ChocolateyPackageName
    fileType      = 'MSI'
    url           = $url
    url64         = $url
    checksum      = '0D598CCE56CF6D3272D5E1B1C1266B5F5C816FC367D61D2113EAA41F07D1FC18'
    checksumType  = 'sha256'
    checksum64    = '0D598CCE56CF6D3272D5E1B1C1266B5F5C816FC367D61D2113EAA41F07D1FC18'
    checksumType64= 'sha256'
    softwareName  = 'cisco-secure-client*'
    # MSI
    silentArgs    = "/norestart /passive /lvx* `"$($env:TEMP)\$($packageName).$($env:chocolateyPackageVersion).MsiInstall.log`"" # ALLUSERS=1 DISABLEDESKTOPSHORTCUT=1 ADDDESKTOPICON=0 ADDSTARTMENU=0
    validExitCodes= @(0, 3010, 1641)
}


Install-ChocolateyPackage @packageArgs


$exePath = Join-Path "$($env:SystemDrive)\Program Files (x86)\Cisco\Cisco Secure Client" 'vpncli.exe'


Install-ChocolateyPath "$($env:SystemDrive)\Program Files (x86)\Cisco\Cisco Secure Client" -PathType Machine


$installLocation = "$($env:SystemDrive)\Program Files (x86)\Cisco\Cisco Secure Client"
if (!$installLocation)  { Write-Warning "Can't find cisco secure client install location"; return }
Write-Host "cisco-secure-client installed to '$installLocation'"

Install-BinFile 'vpncli' $installLocation\vpncli.exe

