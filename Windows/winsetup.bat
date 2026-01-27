@echo off

rem Enter the password you want used for your Windows account
set DESIRED_PASSWORD=

echo Elevating if not admin
NET FILE 1>NUL 2>NUL
if %errorlevel% NEQ 0 (
  powershell Start-Process -FilePath "%0" -verb runas >NUL 2>&1
  exit /b
)

echo Prevent future bloatware
reg add "HKCU\Software\Policies\Microsoft\Windows\CloudContent" /v DisableCloudOptimizedContent /d 1 /t REG_DWORD /f
reg add "HKCU\Software\Policies\Microsoft\Windows\CloudContent" /v DisableWindowsConsumerFeatures /d 1 /t REG_DWORD /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v ContentDeliveryAllowed /d 0 /t REG_DWORD /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SilentInstalledAppsEnabled /d 0 /t REG_DWORD /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\ContentDeliveryManager" /v SystemPaneSuggestionsEnabled /d 0 /t REG_DWORD /f
reg add "HKCU\Software\Policies\Microsoft\Windows\Explorer" /v HideRecommendedSection /d 1 /t REG_DWORD /f

echo Disable Telemetry
reg add "HKLM\Software\Policies\Microsoft\Windows\DataCollection" /v AllowTelemetry /d 0 /t REG_DWORD /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\AppCompat" /v AITEnable /t REG_DWORD /d 0 /f

echo Disable Connected User Experiences and Telemetry (aka DiagTrack)
net stop DiagTrack
sc config DiagTrack start=disabled

echo Disable diagnostic logging
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Diagnostics\Performance" /v DisableDiagnosticTracing /d 1 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Diagnostics\Performance\BootCKCLSettings" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Diagnostics\Performance\SecondaryLogonCKCLSettings" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Diagnostics\Performance\ShutdownCKCLSettings" /v Start /d 0 /t REG_DWORD /f

echo Disable diagnostic policy service (aka RADAR)
sc config DPS start=disabled

echo Disable ETL logging (reduces disk I/O)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\CloudExperienceHostOobe" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\DiagLog" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\Diagtrack-Listener" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\ReadyBoot" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\WDIContextLog" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\WiFiDriverIHVSession" /v Start /d 0 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\WiFiSession" /v Start /d 0 /t REG_DWORD /f

echo Limit logging that can't be disabled (significantly reduces disk I/O)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\DefenderApiLogger" /v MaxFileSize /d 1 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\DefenderApiLogger" /v LogFileMode /d 0x00000100 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\EventLog-System" /v MaxFileSize /d 1 /t REG_DWORD /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\WMI\Autologger\EventLog-System" /v LogFileMode /d 0x00000100 /t REG_DWORD /f

echo Block IrisService
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\IrisService" /v LastContextDate /d "9999-01-01T12:00:00Z" /t REG_SZ /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\IrisService\Providers\CTAC" /v UpdateTime /d "9999-01-01T12:00:00Z" /t REG_SZ /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\IrisService\Providers\Display" /v UpdateTime /d "9999-01-01T12:00:00Z" /t REG_SZ /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\IrisService\Providers\Storage" /v UpdateTime /d "9999-01-01T12:00:00Z" /t REG_SZ /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\IrisService\Providers\Storage" /v FreeSpace /d 0 /t REG_QWORD /f
set IRIS_SERVICE_PATH=%SystemRoot%\SystemApps\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\IrisService.dll
if exist "%IRIS_SERVICE_PATH%" (
  takeown /f "%IRIS_SERVICE_PATH%"
  icacls  "%IRIS_SERVICE_PATH%" /grant administrators:F
  rename "%IRIS_SERVICE_PATH%" "IrisService.dll.x"
)

echo Disable advertising id
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" /v Enabled /d 0 /t REG_DWORD /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo" /v DisabledByGroupPolicy /d 1 /t REG_DWORD /f

echo Turn off inking and typing personalization
reg add "HKCU\Software\Microsoft\InputPersonalization" /v RestrictImplicitInkCollection /d 1 /t REG_DWORD /f
reg add "HKCU\Software\Microsoft\InputPersonalization" /v RestrictImplicitTextCollection /d 1 /t REG_DWORD /f
reg add "HKCU\Software\Microsoft\InputPersonalization\TrainedDataStore" /v HarvestContacts /d 0 /t REG_DWORD /f
reg add "HKCU\Software\Microsoft\Personalization\Settings" /v AcceptedPrivacyPolicy /d 0 /t REG_DWORD /f

echo Disable websites' access to language list
reg add "HKCU\Control Panel\International\User Profile" /v HttpAcceptLanguageOptOut /d 1 /t REG_DWORD /f

echo Disable Bing search in start
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Search" /v BingSearchEnabled /d 0 /t REG_DWORD /f

echo Disable feedback
reg add "HKCU\Software\Microsoft\Siuf\Rules" /v NumberOfSIUFInPeriod /d 0 /t REG_DWORD /f

echo Disable CEIP tasks
schtasks /change /TN "\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Application Experience\ProgramDataUpdater" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Customer Experience Improvement Program\Consolidator" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Customer Experience Improvement Program\KernelCeipTask" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip" /DISABLE

echo Disable device census
schtasks /change /TN "\Microsoft\Windows\Device Information\Device" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Device Information\Device User" /DISABLE

echo Disable Enterprise Data Protection Policy task
schtasks /change /TN "\Microsoft\Windows\AppID\EDP Policy Manager" /DISABLE

echo Disable Enterprise Management task
schtasks /change /TN "\Microsoft\Windows\EnterpriseMgmt\MDMMaintenenceTask" /DISABLE

echo Disabe Compatibility Telemetry
schtasks /change /TN "\Microsoft\Windows\Application Experience\MareBackup" /DISABLE
schtasks /change /TN "\Microsoft\Windows\Application Experience\ProgramDataUpdater" /DISABLE

echo Disable 3rd party tasks
schtasks /change /TN "\Intel\Intel Telemetry 2 (x86)" /DISABLE

echo Disable wap push
net stop dmwappushservice
sc config dmwappushservice start=disabled

echo Disable work folders client
dism /online /Disable-Feature /FeatureName:WorkFolders-Client /Quiet /NoRestart

echo Prevent apps and search from running in background (lowers memory usage but may make apps take longer to start)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications" /v GlobalUserDisabled /d 1 /t REG_DWORD /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Search" /v BackgroundAppGlobalToggle /d 0 /t REG_DWORD /f

echo Enable memory compression
powershell -c "Enable-MMAgent -MemoryCompression"

echo Prevent Edge from running at startup
powershell -c "Remove-ItemProperty -Path HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run -Name Microsoft*Edge*"

REM echo Prevent OneDrive from running at startup
REM powershell -c "Remove-ItemProperty -Path HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run -Name OneDrive"

echo Disable running UWPs at startup
reg add "HKCR\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData\Microsoft.SkypeApp_kzf8qxf38zg5c\SkypeStartup" /v State /d 0 /t REG_DWORD /f
reg add "HKCR\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData\Microsoft.549981C3F5F10_8wekyb3d8bbwe\CortanaStartupId" /v State /d 0 /t REG_DWORD /f

echo Set some services to delay-start to improve startup times
sc config CryptSvc start=delayed-auto
sc config DeviceAssociationService start=delayed-auto
sc config EventSystem start=delayed-auto
sc config "GameInput Service" start=delayed-auto
sc config IKEEXT start=delayed-auto
sc config iphlpsvc start=delayed-auto
sc config LanmanServer start=delayed-auto
sc config NlaSvc start=delayed-auto
sc config nsi start=delayed-auto
sc config RasMan start=delayed-auto
sc config stisvc start=delayed-auto
sc config TrkWks start=delayed-auto
sc config UserManager start=delayed-auto
sc config UWPService start=delayed-auto
sc config Winmgmt start=delayed-auto
sc config WpnService start=delayed-auto

echo Disable superfetch and app pre-launch
sc config SysMain start=demand
net start SysMain
powershell "Disable-MMAgent -ApplicationPreLaunch"
net stop SysMain
sc config SysMain start=disabled

echo Disable prefetcher
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters" /v EnablePrefetcher /t REG_DWORD /d 0 /f

echo Prioritize forground processes 3:1 to background process using a fixed, short time slice
reg add "HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl" /v Win32PrioritySeparation /d 0x2A /t REG_DWORD /f

echo Align taskbar left
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced /v TaskbarAl /t REG_DWORD /d 0 /f

echo Hide taskbar buttons
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced /v TaskbarMn /t REG_DWORD /d 0 /f
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Search /v SearchboxTaskbarMode /t REG_DWORD /d 0 /f
reg add HKLM\SOFTWARE\Policies\Microsoft\Dsh /v AllowNewsAndInterests /t REG_DWORD /d 0 /f

echo Add touch keyboard button
reg add HKCU\SOFTWARE\Microsoft\TabletTip\1.7 /v TipbandDesiredVisibility /t REG_DWORD /d 1 /f

echo Set touch keyboard to traditional/full keyboard
reg add HKCU\SOFTWARE\Microsoft\TabletTip\1.7 /v EnableCompatibilityKeyboard /t REG_DWORD /d 1 /f
reg add HKCU\SOFTWARE\Microsoft\TabletTip\1.7 /v KeyboardLayoutPreference /t REG_DWORD /d 1 /f

echo Enable End Task in Right Click Menu
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced\TaskbarDeveloperSettings /v TaskbarEndTask /t REG_DWORD /d 1 /f

echo Show file extensions in Explorer
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced /v HideFileExt /t REG_DWORD /d 0 /f

echo Set accent color
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent /v AccentColorMenu /t REG_DWORD /d 0xff0b570b /f
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent /v StartColorMenu /t REG_DWORD /d 0xff0b570b /f
reg add HKCU\Software\Microsoft\Windows\DWM /v AccentColor /t REG_DWORD /d 0xff0b570b /f
for /f %%i in ('wmic useraccount where name^="%USERNAME%" get sid ^| findstr ^S\-d*') do set SID=%%i
reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\SystemProtectedUserData\%SID%\AnyoneRead\Colors /v AccentColor /t REG_DWORD /d 0xff0b570b /f
reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\SystemProtectedUserData\%SID%\AnyoneRead\Colors /v StartColor /t REG_DWORD /d 0xff0b570b /f

echo Add accent color to taskbar and start menu
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize /v ColorPrevalence /t REG_DWORD /d 1 /f

echo Add accent color to window titlebars and borders
reg add HKCU\Software\Microsoft\Windows\DWM /v ColorPrevalence /t REG_DWORD /d 1 /f

echo Set dark mode
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize /v AppsUseLightTheme /t REG_DWORD /d 0 /f
reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize /v SystemUsesLightTheme /t REG_DWORD /d 0 /f

echo Set wallpaper (won't take effect until reboot)
reg add "HKCU\control panel\desktop" /v wallpaper /t REG_SZ /d "%SystemRoot%\Web\Wallpaper\ThemeA\img23.jpg" /f

echo Set the desired password for the local account (default value is blank)
if defined DESIRED_PASSWORD (
  net user "%USERNAME%" "%DESIRED_PASSWORD%"
) else (
  net user "%USERNAME%" ""
)

echo Enable auto login
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v AutoAdminLogon /t REG_SZ /d "1" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultUserName /t REG_SZ /d "%USERNAME%" /f
if defined DESIRED_PASSWORD (
  reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword /t REG_SZ /d "%DESIRED_PASSWORD%" /f
) else (
  reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword /t REG_SZ /d "" /f
)

echo Set display scale and orientation
pushd "%~dp0"
powershell -ExecutionPolicy Bypass -c ". .\DisplayHelper.ps1; Set-ScaleAndOrientation"
popd

echo Setup Edge (must be done before first run)
reg query "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v AddressBarMicrosoftSearchInBingProviderEnabled
if %errorlevel% NEQ 0 (
  SET NEED_MSA=1
) ELSE (
  SET NEED_MSA=0
)
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v AddressBarMicrosoftSearchInBingProviderEnabled /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v AdsSettingForIntrusiveAdsSites /t REG_DWORD /d 2 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ConfigureDoNotTrack /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v DefaultSearchProviderEnabled /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v DefaultSearchProviderName /t REG_SZ /d "Google" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v DefaultSearchProviderSearchURL /t REG_SZ /d "url: {google:baseURL}search?q=%s&{google:RLZ}{google:originalQueryForSuggestion}{google:assistedQueryStats}{google:searchFieldtrialParameter}{google:iOSSearchLanguage}{google:searchClient}{google:sourceId}{google:contextualSearchVersion}ie={inputEncoding}" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v DefaultSearchProviderSuggestURL /t REG_SZ /d "{google:baseURL}complete/search?output=chrome&q={searchTerms}" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v EdgeShoppingAssistantEnabled /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v StartupBoostEnabled /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v DefaultBrowserSettingEnabled /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ShowRecommendationsEnabled /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportAutofillFormData /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportBrowserSettings /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportHistory /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportCookies /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportExtensions /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportFavorites /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportHomepage /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportOpenTabs /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportPaymentInfo /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportSavedPasswords /t REG_DWORD /d 0 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Edge" /v ImportSearchEngine /t REG_DWORD /d 0 /f

if %NEED_MSA% NEQ 0 (
  echo Launching Edge and OneDrive so sync can be setup
  pushd "%ProgramFiles(x86)%\Microsoft\Edge\Application"
  start msedge.exe
  popd
  pushd "%LocalAppData%\Microsoft\OneDrive"
  start OneDrive.exe
  popd
)

echo Disable fast startup (improves reliability of booting into Windows when dual-booting)
powercfg /hibernate off
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power" /v HiberbootEnabled /d 0 /t REG_DWORD /f

echo Disable modern standby
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Power" /v PlatformAoAcOverride /d 0 /t REG_DWORD /f

echo Set various 3rd party driver services to manual
sc config HPPrintScanDoctorService start=demand
sc config NVDisplay.ContainerLocalSystem start=demand
sc config FvSvc start=demand
sc config NvContainerLocalSystem start=disabled
REM sc config RtkAudioUniversalService start=demand
sc config HKClipSvc start=demand
sc config PowerBiosServer start=demand
sc config XTU3SERVICE start=demand
sc config xTendSoftAPService start=demand
sc config xTendUtilityService start=demand
sc config WDDriveService start=demand

REM echo Starting QuickAssist
REM explorer shell:appsFolder\MicrosoftCorporationII.QuickAssist_8wekyb3d8bbwe!App

REM echo Download and start AnyDesk
REM if not exist "%TEMP%\AnyDeskDL\AnyDesk.exe" (
  REM mkdir "%TEMP%\AnyDeskDL"
  REM powershell -c "Invoke-WebRequest -URI 'https://download.anydesk.com/AnyDesk.exe' -OutFile $env:TEMP'\AnyDeskDL\AnyDesk.exe'"
REM )
REM pushd "%TEMP%\AnyDeskDL"
REM start AnyDesk.exe
REM popd

echo Remove existing bloatware
winget uninstall "Clipchamp"
winget uninstall "Spotify Music"
winget uninstall "Disney+"
winget uninstall "Microsoft Teams"
winget uninstall "Messenger"
winget uninstall "Adobe Express"
winget uninstall "TikTok"
winget uninstall "Prime Video for Windows"
winget uninstall "Camo Studio"
winget uninstall "WhatsApp"
winget uninstall "LinkedIn"

REM Broken on latest Windows 11 by https://github.com/MicrosoftDocs/windows-powershell-docs/issues/3267
REM Should start working again on its own once the issue is fixed
echo Remove pinned bloatware from Start Menu
powershell -c "$f=$env:TEMP+'\winsetup_start_layout'; Export-StartLayout $f; ((Get-Content $f) -replace '<[^<]+SpotifyAB.SpotifyMusic[^<]+>','' -replace '<[^<]+ReincubateLtd.CamoStudio[^<]+>','' -replace '<[^<]+LinkedInforWindows[^<]+>','' -replace '<[^<]+WhatsAppDesktop[^<]+>','' -replace '<[^<]+Clipchamp.Clipchamp[^<]+>','' -replace '\{[^\{]+SpotifyAB.SpotifyMusic[^\{]+\}\,?','' -replace '\{[^\{]+ReincubateLtd.CamoStudio[^\{]+\}\,?','' -replace '\{[^\{]+LinkedInforWindows[^\{]+\}\,?','' -replace '\{[^\{]+WhatsAppDesktop[^\{]+\}\,?','' -replace '\{[^\{]+Clipchamp.Clipchamp[^\{]+\}\,?','') | Out-File $f; Import-StartLayout -LayoutPath $f -MountPath $env:SystemDrive'\'"

REM Disabled due to the 2302270303 APU driver causing crashes on recent versions of Windows
REM echo Enable core isolation
REM reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity" /v Enabled /d 1 /t REG_DWORD /f

echo Enable controlled folder access
powershell -c "Set-MpPreference -EnableControlledFolderAccess Enabled"

echo Fix real time clock offset to match Linux/SteamOS
reg add "HKLM\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f

echo Set time service to auto and start it
sc config W32Time start=auto
net start W32Time

echo Run NetSync (Synchronizes time, updates everything and ensures Windows does not set itself as your default OS)
cmd /c "%~dp0\NetSync.bat"

echo Install drivers
rem Drivers from https://help.steampowered.com/en/faqs/view/6121-ECCD-D643-BAA8

if not exist "%TEMP%\DriverDL" (
  mkdir %TEMP%\DriverDL
)

if not exist "%TEMP%\DriverDL\apu_driver.zip" (
  powershell -c "Invoke-WebRequest -URI 'https://steamdeck-packages.steamos.cloud/misc/windows/drivers/Aerith Windows Driver_2302270303.zip' -OutFile $env:TEMP'\DriverDL\apu_driver.zip'"
  powershell -c "Expand-Archive -Path $env:TEMP'\DriverDL\apu_driver.zip' -DestinationPath $env:TEMP'\DriverDL'"
  cmd /c "%TEMP%\DriverDL\GFX Driver_41.1.1.30310_230227a-388790E-2302270303\Setup.exe" -install
)

if not exist "%TEMP%\DriverDL\audio_driver_1.zip" (
  powershell -c "Invoke-WebRequest -URI 'https://steamdeck-packages.steamos.cloud/misc/windows/drivers/cs35l41-V1.2.1.0.zip' -OutFile $env:TEMP'\DriverDL\audio_driver_1.zip'"
  powershell -c "Expand-Archive -Path $env:TEMP'\DriverDL\audio_driver_1.zip' -DestinationPath $env:TEMP'\DriverDL'"
  pushd "%TEMP%\DriverDL\cs35l41-V1.2.1.0"
  pnputil -i -a cs35l41.inf
  popd
)

if not exist "%TEMP%\DriverDL\audio_driver_2.zip" (
  powershell -c "Invoke-WebRequest -URI 'https://steamdeck-packages.steamos.cloud/misc/windows/drivers/NAU88L21_x64_1.0.6.0_WHQL - DUA_BIQ_WHQL.zip' -OutFile $env:TEMP'\DriverDL\audio_driver_2.zip'"
  powershell -c "Expand-Archive -Path $env:TEMP'\DriverDL\audio_driver_2.zip' -DestinationPath $env:TEMP'\DriverDL'"
  pushd "%TEMP%\DriverDL\NAU88L21_x64_1.0.6.0_WHQL - DUA_BIQ_WHQL"
  pnputil -i -a NAU88L21.inf
  popd
)

if not exist "%TEMP%\DriverDL\bt_driver.zip" (
  powershell -c "Invoke-WebRequest -URI 'https://steamdeck-packages.steamos.cloud/misc/windows/drivers/RTBlueR_FilterDriver_1041.3005_1201.2021_new_L.zip' -OutFile $env:TEMP'\DriverDL\bt_driver.zip'"
  powershell -c "Expand-Archive -Path $env:TEMP'\DriverDL\bt_driver.zip' -DestinationPath $env:TEMP'\DriverDL'"
  cmd /c "%TEMP%\DriverDL\RTBlueR_FilterDriver_1041.3005_1201.2021_new_L\installdriver.cmd"
)

echo Download and install Steam
rem  if not exist "%TEMP%\SteamDL" (
rem    mkdir "%TEMP%\SteamDL"
rem    powershell -c "Invoke-WebRequest -URI 'https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe' -OutFile $env:TEMP'\SteamDL\SteamSetup.exe'"
rem    pushd "%TEMP%\SteamDL"
rem    SteamSetup.exe /S
rem    popd
rem  )
winget install -e --id Valve.Steam

echo Install Epic Launcher
winget install -e --id EpicGames.EpicGamesLauncher

echo Install NetSync and set it to run when the device boots or wakes from sleep
if not exist "%ProgramFiles%\NetSyncAndSoftReboot\NetSync.bat" (
  mkdir "%ProgramFiles%\NetSyncAndSoftReboot"
  copy "%~dp0\NetSync.bat" "%ProgramFiles%\NetSyncAndSoftReboot\NetSync.bat"
  powershell -c "Register-ScheduledTask -Action (New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c start /min cmd /c """%ProgramFiles%\NetSyncAndSoftReboot\NetSync.bat"""') -Trigger (@()+(New-ScheduledTaskTrigger -AtLogon)+(New-CimInstance -CimClass (Get-CimClass -Namespace ROOT\Microsoft\Windows\TaskScheduler -ClassName MSFT_TaskSessionStateChangeTrigger) -Property @{StateChange = 8} -ClientOnly)) -Principal (New-ScheduledTaskPrincipal -UserId (Get-CimInstance –ClassName Win32_ComputerSystem | Select-Object -expand UserName) -RunLevel Highest) -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries) -TaskName 'NetSync' -Description 'Keep everything updated and synched'"
)

echo Install SoftReboot and create a desktop shortcut to it
if not exist "%ProgramFiles%\NetSyncAndSoftReboot\SoftReboot.bat" (
  mkdir "%ProgramFiles%\NetSyncAndSoftReboot"
  copy "%~dp0\SoftReboot.bat" "%ProgramFiles%\NetSyncAndSoftReboot\SoftReboot.bat"
  powershell -c "$sh=New-Object -comObject WScript.Shell; $s=$sh.CreateShortcut($Home+'\Desktop\SoftReboot.lnk'); $s.TargetPath=$Env:ProgramFiles+'\NetSyncAndSoftReboot\SoftReboot.bat'; $s.IconLocation=$Env:SystemRoot+'\System32\SHELL32.dll,12'; $s.Save()"
)

if not exist "%USERPROFILE%\Programs" (
  mkdir "%USERPROFILE%\Programs"
)

REM echo Install PS Remote Play
REM winget install -e --id Microsoft.VC++2015-2019Redist-x86
REM if not exist "%TEMP%\PSRemotePlayDL" (
  REM mkdir "%TEMP%\PSRemotePlayDL"
  REM powershell -c "Invoke-WebRequest -URI 'https://remoteplay.dl.playstation.net/remoteplay/module/win/RemotePlayInstaller.exe' -OutFile $env:TEMP'\PSRemotePlayDL\RemotePlayInstaller.exe'"
  REM pushd RemotePlayInstaller.exe
  REM RemotePlayInstaller.exe /S /v/qn
  REM popd
REM )



echo Add GlosSI shortcuts to Steam
if exist "%AppData%\GlosSi" (
  powershell -c "Get-ChildItem -Directory '%ProgramFiles(x86)%\Steam\userdata' | ForEach-Object { $sh=$_.FullName+'\config\shortcuts.vdf'; if ((Test-Path $sh) -and ((Get-Content $sh) -notlike '*GlosSI*')){ [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('c2hvcnRjdXRzICAwIAJhcHBpZCACQ1PihKIBYXBwbmFtZSBHbG9zU0kgAUV4ZSAiWFVTRVJcUHJvZ3JhbXNcR2xvc1NpXEdsb3NTSVRhcmdldC5leGUiIAFTdGFydERpciAiWFVTRVJcUHJvZ3JhbXNcR2xvc1NpXCIgAWljb24gIAFTaG9ydGN1dFBhdGggIAFMYXVuY2hPcHRpb25zIEdsb3NTSS5qc29uIAJJc0hpZGRlbiAgICAgAkFsbG93RGVza3RvcENvbmZpZyABICAgAkFsbG93T3ZlcmxheSABICAgAk9wZW5WUiAgICAgAkRldmtpdCAgICAgAURldmtpdEdhbWVJRCAgAkRldmtpdE92ZXJyaWRlQXBwSUQgICAgIAJMYXN0UGxheVRpbWUg4oCUdDNjAUZsYXRwYWtBcHBJRCAgIHRhZ3MgCAggMSACYXBwaWQgKMK0IMOxAWFwcG5hbWUgR2xvc1NJLURTNCABRXhlICJYVVNFUlxQcm9ncmFtc1xHbG9zU2lcR2xvc1NJVGFyZ2V0LmV4ZSIgAVN0YXJ0RGlyICJYVVNFUlxQcm9ncmFtc1xHbG9zU2lcIiABaWNvbiAgAVNob3J0Y3V0UGF0aCAgAUxhdW5jaE9wdGlvbnMgZ2xvc3NpLWRzNC5qc29uIAJJc0hpZGRlbiAgICAgAkFsbG93RGVza3RvcENvbmZpZyABICAgAkFsbG93T3ZlcmxheSABICAgAk9wZW5WUiAgICAgAkRldmtpdCAgICAgAURldmtpdEdhbWVJRCAgAkRldmtpdE92ZXJyaWRlQXBwSUQgICAgIAJMYXN0UGxheVRpbWUgHnkzYwFGbGF0cGFrQXBwSUQgICB0YWdzIAgICAg=')).Replace('XUSER',$HOME) | Set-Content ($sh+'.test')}}"
)



echo Install WinDirStat
winget install -e --id WinDirStat.WinDirStat

echo Installing Minecraft, click install to continue
start ms-windows-store://pdp/?ProductId=9NBLGGH2JHXJ^&mode=mini

pause
