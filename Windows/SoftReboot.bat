rem This utility performs a "soft reboot", resetting several parts of Windows to how they would be after a reboot
rem This can be used to free up memory and resolve various issues

rem Elevating if not admin
NET FILE 1>NUL 2>NUL
if %errorlevel% NEQ 0 (
  powershell Start-Process -FilePath "%0" -verb runas >NUL 2>&1
  exit /b
)

taskkill /f /im Xbox*
taskkill /f /im EABackground*
taskkill /f /im EAConnect*
taskkill /f /im upc.exe
taskkill /f /im Uplay*

taskkill /f /im dwm.exe
taskkill /f /im LockApp.exe
taskkill /f /im SearchApp.exe
taskkill /f /im SearchFilterHost.exe
taskkill /f /im SearchProtocolHost.exe
taskkill /f /im SearchIndexer.exe
taskkill /f /im SearchHost.exe
taskkill /f /im SystemSettingsBroker.exe
taskkill /f /im StartMenuExperienceHost.exe
taskkill /f /im ShellExperienceHost.exe
taskkill /f /im TextInputHost.exe
taskkill /f /im TabTip.exe
taskkill /f /im osk.exe
taskkill /f /im magnify.exe
taskkill /f /im RuntimeBroker.exe
taskkill /f /im UserOOBEBroker.exe
taskkill /f /im SpeechRuntime.exe
taskkill /f /im spoolsv.exe
taskkill /f /im ctfmon.exe
taskkill /f /im audiodg.exe
taskkill /f /im explorer.exe
taskkill /f /im sihost.exe

taskkill /f /im nv*
taskkill /f /im Creative.UWPRPCService.exe

wmic Path win32_process Where "CommandLine Like '%{3EB3C877-1F16-487C-9050-104DBCD66683}%'" Call Terminate
wmic Path win32_process Where "CommandLine Like '%{776DBC8D-7347-478C-8D71-791E12EF49D8}%'" Call Terminate
wmic Path win32_process Where "CommandLine Like '%{AB8902B4-09CA-4BB6-B78D-A8F59079A8D5}%'" Call Terminate
wmic Path win32_process Where "CommandLine Like '%RxDiagSetRuntimeMessagePump%'" Call Terminate

taskkill /f /im Wmiadap.exe
taskkill /f /im wmiprvse.exe

rem start explorer
