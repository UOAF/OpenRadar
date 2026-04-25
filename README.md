UOAF OpenRadar for BMS Falcon 4.0

![screenshot](https://github.com/UOAF/OpenRadar/blob/main/Data/Screenshot.png)

## Getting Started
1. Download OpenRadar.exe from the release on github
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
When you run OpenRadar.exe, a config file will be generated in the same directory called "OpenRadar.toml"
This file contains a bunch of configuration stuff that you can change in the file, or through the in-program settings.

This line dictates what icon set the program will use. You cannot change this in the application.

    ```
    [display]
    icon_set = "NTDS" # Icon set to use for displaying objects (NTDS, classic)
    ```
Classic = Classic OpenRadar icons

NTDS = Naval Tactical Data System symbology. You can change each faction's relation in the Coalition tab. 
<img src="https://github.com/ValerieOSD/OpenRadar/blob/6f586ed2f2ad9cdd3d7d780e9b5a8bfe224d9d71/Data/NTDS.png" width="600">


You can also customize the track labels of all targets visible on OpenRadar with your own text, or through the usage of variables such as speed, altitude, fuel, bullseye position and more.
List of variables [here](https://github.com/ValerieOSD/OpenRadar/wiki/Track-Label-Variables).
<img src="https://github.com/ValerieOSD/OpenRadar/blob/493ca90e8d328af058e5955ba3d9175ae4a5c1ad/Data/TrackLabels.png" width="600">

## Work in Progress
This project is a work in progress. Features and functionalities are continuously being developed and improved. Some features will be incomplete or not functional. Your feedback and contributions are highly appreciated to help us enhance the tool.

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
