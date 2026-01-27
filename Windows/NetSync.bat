@echo off
rem This utility syncs the clock, updates Windows, apps, and antivirus definitions and ensures that Windows will not set itself as the default OS to boot

rem Synchronize clock, retry up to $MAX times in case internet isn't ready yet
powershell -c "$MAX=30;$i=0;while(1){if($i -gt $MAX){exit 1;}$res=w32tm /resync;Write-Host $res;if($res -like '*completed successfully*'){exit 0;}start-sleep -s 5;$i++}"
if %errorlevel% NEQ 0 goto ERROR_TIMESYNC

rem Wait for internet to be available, unused/flaky
rem powershell -c "$MAX=30;$i=0;while(((gwmi -class Win32_NetworkAdapterConfiguration -filter DHCPEnabled=TRUE | where{$_.DefaultIPGateway -ne $null})|measure).count -lt 1){if($i -gt $MAX){exit 1;}start-sleep -s 1;$i++};exit 0;"

rem Check for Windows updates
usoclient startinteractivescan
if %errorlevel% NEQ 0 goto ERROR_WINUPDATECHECK

rem Update store apps
powershell -c "(Get-WmiObject -Namespace 'root\cimv2\mdm\dmmap' -Class 'MDM_EnterpriseModernAppManagement_AppManagement01').UpdateScanMethod()"
if %errorlevel% NEQ 0 goto ERROR_STOREAPPS

rem Update Edge
"%ProgramFiles(x86)%\Microsoft\EdgeUpdate\MicrosoftEdgeUpdate.exe" /update
if %errorlevel% NEQ 0 goto ERROR_EDGEUPDATE

rem Update Defender definitions
"%ProgramFiles%\Windows Defender\MpCmdRun.exe" -SignatureUpdate
if %errorlevel% NEQ 0 goto ERROR_DEFENDERUPDATE

rem Force Windows updates to install if they haven't already
rem This seems to be a noop on recent versions of Windows
usoclient startinstall
if %errorlevel% NEQ 0 goto ERROR_WINUPDATEINSTALL

rem Keep Windows from taking over the boot manager
rem Assumes \EFI\null.efi doesn't exist and that the firmware will fallback to using the default boot order
bcdedit /set {bootmgr} path \EFI\null.efi
if %errorlevel% NEQ 0 goto ERROR_BOOTMGR

timeout /nobreak 15
goto NO_ERROR


rem Error Codes

:NO_ERROR
exit 0

:ERROR_TIMESYNC
exit 1

:ERROR_WINUPDATECHECK
exit 2

:ERROR_STOREAPPS
exit 3

:ERROR_EDGEUPDATE
exit 4

:ERROR_DEFENDERUPDATE
exit 5

:ERROR_WINUPDATEINSTALL
exit 6

:ERROR_BOOTMGR
exit 7
