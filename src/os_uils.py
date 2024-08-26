import subprocess
import winreg

def open_file_dialog():
    
    start_dir = get_bms_path_reg()
    if start_dir is None:  start_dir = "[System.IO.Directory]::GetCurrentDirectory()"
    else: start_dir = f'"{start_dir}\\data"'
    PS_Commands = ""
    PS_Commands += "Add-Type -AssemblyName System.Windows.Forms;"
    PS_Commands += "$fileBrowser = New-Object System.Windows.Forms.OpenFileDialog;"
    PS_Commands += "$fileBrowser.InitialDirectory =" + str(start_dir) + ";"
    PS_Commands += "$Null = $fileBrowser.ShowDialog();"
    PS_Commands += "echo $fileBrowser.FileName"
    file_path = subprocess.run(["powershell.exe", PS_Commands], stdout=subprocess.PIPE)
    file_path = file_path.stdout.decode()
    file_path = file_path.rstrip()
    return file_path

def get_bms_path_reg():
    
    bms_installs = list()
    # Computer\HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Benchmark Sims\Falcon BMS 4.37
    key = r'SOFTWARE\WOW6432Node\Benchmark Sims'
    aReg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    parent_Key = winreg.OpenKey(aReg, key)

    # Enumerate all the subkeys (different BMS versions)
    for i in range(1024):
        try:
            bms_version = winreg.EnumKey(parent_Key, i)
            bms_version_key = winreg.OpenKey(parent_Key, bms_version)
            sValue = winreg.QueryValueEx(bms_version_key, "baseDir")[0]
            bms_installs.append((bms_version, sValue))
        except FileNotFoundError:
            print("Falcon BMS not found in registry")
            break
        except EnvironmentError:
            break
    
    if len(bms_installs) == 0:
        return None
    # Return the latest BMS version path, this could also be used to get the current installed BMS version
    return sorted(bms_installs, key=lambda x: x[0])[-1][1]