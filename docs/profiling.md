# Profiling OpenRadar

## 1. Find the process ID

Running under VS Code's debugger spawns two `python.exe` processes. Use the one with the much larger working set (hundreds of MB):

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object { $_.CommandLine -match 'OpenRadar\.py' } |
  Select-Object ProcessId, CommandLine

Get-Process -Id <id1>,<id2> | Select-Object Id, ProcessName, WorkingSet
```

## 2. Live view

Run in an **elevated** terminal (py-spy needs admin on Windows):

```powershell
py-spy top --pid <PID>
```

## 3. Record a flamegraph

```powershell
py-spy record -o profile.svg --pid <PID> --duration 45
```

Open `profile.svg` in a browser. Box width = % of sampled time in that function (including what it calls).

## 4. Comparing before/after

Only compare two runs if the scenario matches: same zoom level, same point in the replay, similar traffic density. Frame cost scales with how many aircraft/labels are on screen, so an uncontrolled comparison can look like a regression (or improvement) that isn't real.

Also check the in-app debug overlay (FPS / GPU / CPU Frame Process Time) for the same reason — same caveat applies.