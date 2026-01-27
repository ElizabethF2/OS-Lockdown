# This utility is used by winsetup to change display orientation
# It is not meant to be called directly

Function Set-ScaleAndOrientation {

$source = @"

using System;
using System.Runtime.InteropServices;

namespace DisplayHelper
{
  [StructLayout(LayoutKind.Sequential)]
  public struct DEVMODE
  {
   [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]
   public string dmDeviceName;

   public short  dmSpecVersion;
   public short  dmDriverVersion;
   public short  dmSize;
   public short  dmDriverExtra;
   public int    dmFields;
   public int    dmPositionX;
   public int    dmPositionY;
   public int    dmDisplayOrientation;
   public int    dmDisplayFixedOutput;
   public short  dmColor;
   public short  dmDuplex;
   public short  dmYResolution;
   public short  dmTTOption;
   public short  dmCollate;

   [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
   public string dmFormName;

   public short  dmLogPixels;
   public short  dmBitsPerPel;
   public int    dmPelsWidth;
   public int    dmPelsHeight;
   public int    dmDisplayFlags;
   public int    dmDisplayFrequency;
   public int    dmICMMethod;
   public int    dmICMIntent;
   public int    dmMediaType;
   public int    dmDitherType;
   public int    dmReserved1;
   public int    dmReserved2;
   public int    dmPanningWidth;
   public int    dmPanningHeight;
  };

  class Consts
  {
    public const int ENUM_CURRENT_SETTINGS = -1;

    public const int CDS_UPDATEREGISTRY = 0x01;
    public const int CDS_TEST = 0x02;

    public const int DISP_CHANGE_SUCCESSFUL = 0;
    public const int DISP_CHANGE_RESTART = 1;
    public const int DISP_CHANGE_FAILED = -1;

    public const int DMDO_DEFAULT = 0;
    public const int DMDO_90 = 1;
    public const int DMDO_180 = 2;
    public const int DMDO_270 = 3;

    public const int SPI_GETLOGICALDPIOVERRIDE = 0x009E;
    public const int SPI_SETLOGICALDPIOVERRIDE = 0x009F;

    public const int SPIF_UPDATEINIFILE  = 0x1;
  }

  class NativeMethods
  {
    [DllImport("user32.dll")]
    public static extern int EnumDisplaySettings(string lpszDeviceName, int iModeNum, ref DEVMODE lpDevMode);

    [DllImport("user32.dll")]
    public static extern int ChangeDisplaySettings(ref DEVMODE lpDevMode, int dwFlags);

    [DllImport("user32.dll")]
    public static extern int SystemParametersInfo(int uiAction, int uiParam, ref int pvParam, int fWinIni);
  }

  public class ScaleAndOrientationSetter
  {
    static public string Set()
    {
      int TARGET_ORIENTATION = Consts.DMDO_270;
      int TARGET_SCALE_INDEX = -1; // 100%

      {
        DEVMODE dm = new DEVMODE();
        dm.dmDeviceName = new String(new char[32]);
        dm.dmFormName = new String(new char[32]);
        dm.dmSize = (short)Marshal.SizeOf(dm);

        if (NativeMethods.EnumDisplaySettings(null, Consts.ENUM_CURRENT_SETTINGS, ref dm) != 0)
        {
          if (dm.dmDisplayOrientation != TARGET_ORIENTATION)
          {
            dm.dmDisplayOrientation = TARGET_ORIENTATION;

            var ret = NativeMethods.ChangeDisplaySettings(ref dm, Consts.CDS_TEST);
            if (ret == Consts.DISP_CHANGE_FAILED)
            {
              return "DISP_CHANGE_FAILED";
            }
            else
            {
              ret = NativeMethods.ChangeDisplaySettings(ref dm, Consts.CDS_UPDATEREGISTRY);
              if (ret != Consts.DISP_CHANGE_SUCCESSFUL && ret != Consts.DISP_CHANGE_RESTART)
              {
                return "CDS_UPDATEREGISTRY failed with " + ret;
              }
            }
          }
        }
      }

      {
        int unused = 0;
        var ret = NativeMethods.SystemParametersInfo(Consts.SPI_SETLOGICALDPIOVERRIDE, TARGET_SCALE_INDEX, ref unused, Consts.SPIF_UPDATEINIFILE);
        if (ret == 0)
        {
          return "SPI_SETLOGICALDPIOVERRIDE failed";
        }
      }

      return "OK";
    }
  }
}

"@

Add-Type $source
$status = [DisplayHelper.ScaleAndOrientationSetter]::Set()
Write-Host "DisplayHelper Status: $status"
}
