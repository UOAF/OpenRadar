UOAF OpenRadar for BMS Falcon 4.0

![screenshot](https://github.com/UOAF/OpenRadar/blob/main/Data/Screenshot.png)

## Requirements
- Windows
- A GPU and drivers supporting **OpenGL 4.6** (core profile)

## Getting Started
1. Download OpenRadar.exe from the [latest release on GitHub](https://github.com/UOAF/OpenRadar/releases)
2. Set the following setting in 'user/config/Falcon BMS User.cfg' to enable Tacview RealTime Telemetry on the BMS host
    ```
    set g_bTacviewRealTime 1
    set g_nTacviewPort 42674
    ```
3. Run OpenRadar.exe and connect to the server in the settings page. Make sure to be in-game and in 3D or telemetry won't be visible!
   
(Optional - P2P)

4. You can also use OpenRadar through Peer to Peer, this means you don't need BMS running or even installed.
Instead you can use someone else's Tacview Real-Time Telemetry, tell them to open their chosen port (Default is 42674) to the internet on their router using their local address, then connect with their public IP!

## Configuration & Customization
When you run OpenRadar.exe, a config file will be generated in the same directory called `openradar.toml`
This file contains a bunch of configuration stuff that you can change in the file, or through the in-program settings.

If the config file ever becomes unreadable, OpenRadar will move it aside to `openradar.toml.corrupt`
and start again from defaults rather than failing to launch.

This line dictates what icon set the program will use. You can also change it in-app under
**File -> Settings**, which writes the same value back to this file.

    [display]
    icon_set = "classic" # Icon set to use for displaying objects (NTDS, classic)

Classic = Classic OpenRadar icons

NTDS = Naval Tactical Data System symbology. You can change each faction's relation in the Coalition tab. 
<img src="https://github.com/UOAF/OpenRadar/blob/main/Data/NTDS.png" width="600">


You can also customize the track labels of all targets visible on OpenRadar with your own text, or through the usage of variables such as speed, altitude, fuel, bullseye position and more.
Labels are edited in-app under **Windows -> Track Labels**; see [docs/label-formats.md](docs/label-formats.md)
for the full syntax and the available variables.
<img src="https://github.com/UOAF/OpenRadar/blob/main/Data/TrackLabels.png" width="600">

## Building from Source
Requires Python 3.12+.

    pip install -r requirements.txt
    python src/OpenRadar.py

Run from the repository root - some resources are resolved relative to the working directory.

To run the tests:

    pytest

To build a standalone executable:

    pyinstaller OpenRadar.spec

## Overview
UOAF OpenRadar is an open-source radar interface tool designed for use with BMS Falcon 4.0. This project aims to 
provide an air battle management radar interface for virtual pilots and controllers. The app connects to BMS via the 
[Tacview Real-Time Telemetry Protocol](https://www.tacview.net/documentation/realtime/en/). Many coming features are 
still WIP or are dependant on data not yet implemented by BMS in TRTT

## Bugs
If you encounter any bugs, please report them on our [GitHub Issues page](https://github.com/UOAF/OpenRadar/issues).
When submitting a bug report, include detailed and reproducible steps to help us diagnose and fix the issue more 
efficiently.

## Feature Requests
We welcome feature requests to improve UOAF OpenRadar. If you have an idea for a new feature, please submit it on our [GitHub Issues page](https://github.com/UOAF/OpenRadar/issues) and label it as a feature request. Provide a detailed description of the feature and its potential benefits to help us understand and prioritize your request.

## Pull Requests
We welcome contributions from the community! If you would like to contribute to UOAF OpenRadar, please follow these steps:
1. Fork the repository on GitHub.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them with clear and concise messages.
4. Push your changes to your forked repository.
5. Open a pull request on our GitHub repository, providing a detailed description of your changes and the problem they solve.

We will review your pull request and provide feedback as needed.

## Join Our Community
We invite new pilots to join our community and fly with us. Connect with us on our [UOAF Discord](https://discord.gg/KGFUjhxWSh) to get started, ask questions, and participate in events.

## License
OpenRadar is licensed under the [GNU General Public License v3.0](LICENSE).
