"""
This module provides classes for parsing and representing ACMI (Air Combat Maneuvering Instrumentation) files.

ACMIEntry:
    Represents an entry in an ACMI file.
    Attributes:
        action (str): The action performed in the entry.
        object_id (str): The ID of the object associated with the entry.
        timestamp (float): The timestamp of the entry.

ACMIObject:
    Represents an object in an ACMI file.
    Inherits from ACMIEntry.
    Attributes:
        properties (dict): The properties of the object.
        AOA (float): Angle of Attack.
        AOS (float): Angle of Sideslip.
        CAS (float): Calibrated Airspeed.
        Coalition (str): The coalition the object belongs to.
        Color (str): The color of the object.
        FuelWeight (float): The weight of the fuel.
        Health (float): The health of the object.
        IAS (float): Indicated Airspeed.
        LateralGForce (float): Lateral G-Force.
        LockedTarget (str): The ID of the primary locked target.
        LockedTarget1-9 (str): The IDs of additional locked targets.
        LongitudinalGForce (float): Longitudinal G-Force.
        Mach (float): The Mach number.
        Name (str): The name of the object.
        Pilot (str): The name of the pilot.
        CallSign (str): The call sign of the object.
        Group (str): The group the object belongs to.
        T (dict): The position information of the object.
        Type (str): The type of the object.
        VerticalGForce (float): Vertical G-Force.

ACMIFileParser:
    Parses an ACMI file and stores the parsed data.
    Attributes:
        file_path (str): The path to the ACMI file.
        global_obj (dict): The global object in the ACMI file.
        objects (dict): The objects in the ACMI file.
        relative_time (float): The relative time of the ACMI file.

"""
from dataclasses import dataclass
from typing import Optional, get_type_hints

import datetime

ACTION_UPDATE = "+"
ACTION_REMOVE = "-"
ACTION_TIME = "#"
ACTION_GLOBAL = "global"


@dataclass
class ACMIEntry:
    """
    Represents an entry in an ACMI (Air Combat Maneuvering Instrumentation) file.

    Attributes:
        action (str): The action performed in the entry.
        object_id (str): The ID of the object associated with the entry.
        timestamp (float): The timestamp of the entry.
    """
    action: str
    timestamp: datetime.datetime
    object_id: Optional[str] = "None"
    delta_time: Optional[float] = None

    # def __init__(self, action: str, object_id: str = "", timestamp: float = 0.0):
    #     self.action = action
    #     self.object_id = object_id
    #     self.timestamp = timestamp


@dataclass
class Orientation:
    """
    This class represents a data structure for storing various attributes of an object.
    
    Attributes:
        Altitude (float): The altitude of the object.
        Heading (float): The heading of the object.
        Latitude (float): The latitude of the object.
        Longitude (float): The longitude of the object.
        Pitch (float): The pitch of the object.
        Roll (float): The roll of the object.
        U (float): The U (X) Position of the object in cartesian coordinates.
        V (float): The V (Y) Position of the object in cartesian coordinates.
        Yaw (float): The yaw of the object.
    """
    Altitude: float = 0.0
    Heading: float = 0.0
    Latitude: float = 0.0
    Longitude: float = 0.0
    Pitch: float = 0.0
    Roll: float = 0.0
    U: float = 0.0
    V: float = 0.0
    Yaw: float = 0.0


@dataclass(kw_only=True)
class ACMIObject(ACMIEntry):
    """
    Represents an ACMI object.

    Attributes:
        object_id (str): The ID of the object.
        properties (dict): The properties of the object.
        AOA (float): The angle of attack of the object.
        AOS (float): The angle of sideslip of the object.
        CAS (float): The calibrated airspeed of the object.
        Coalition (str): The coalition the object belongs to.
        Color (str): The color of the object.
        FuelWeight (float): The weight of the fuel in the object.
        Health (float): The health of the object.
        IAS (float): The indicated airspeed of the object.
        LateralGForce (float): The lateral G-force experienced by the object.
        LockedTarget (str): The ID of the primary locked target.
        LockedTarget1 (str): The ID of locked target 1.
        LockedTarget2 (str): The ID of locked target 2.
        LockedTarget3 (str): The ID of locked target 3.
        LockedTarget4 (str): The ID of locked target 4.
        LockedTarget5 (str): The ID of locked target 5.
        LockedTarget6 (str): The ID of locked target 6.
        LockedTarget7 (str): The ID of locked target 7.
        LockedTarget8 (str): The ID of locked target 8.
        LockedTarget9 (str): The ID of locked target 9.
        LongitudinalGForce (float): The longitudinal G-force experienced by the object.
        Mach (float): The Mach number of the object.
        Name (str): The name of the object.
        Pilot (str): The name of the pilot of the object.
        CallSign (str): The call sign of the object.
        Group (str): The group the object belongs to.
        T (dict): The position and velocity vectors of the object.
        Type (str): The type of the object.
        VerticalGForce (float): The vertical G-force experienced by the object.
    """
    T: Orientation
    timestamp: datetime.datetime
    object_id: str = ""
    properties = dict()
    AOA: float = 0.0
    AOS: float = 0.0
    CAS: float = 0.0
    Coalition: str = ""
    Color: str = "black"
    FuelWeight: float = 0.0
    Health: float = 0.0
    IAS: float = 0.0
    LateralGForce: float = 0.0
    LockedTarget: str = ""
    LockedTarget1: str = ""
    LockedTarget2: str = ""
    LockedTarget3: str = ""
    LockedTarget4: str = ""
    LockedTarget5: str = ""
    LockedTarget6: str = ""
    LockedTarget7: str = ""
    LockedTarget8: str = ""
    LockedTarget9: str = ""
    LongitudinalGForce: float = 0.0
    Mach: float = 0.0
    Name: str = ""
    Pilot: str = ""
    Type: str = ""
    CallSign: str = ""
    Group: str = ""
    VerticalGForce: float = 0.0

    def __init__(self, action, object_id: str, properties: dict, timestamp: datetime.datetime):
        """
        Initialize an ACMIObject object.

        Args:
            action: The action associated with the object.
            object_id (str): The ID of the object.
            properties (dict): The properties of the object.
        """
        super().__init__(action, object_id=object_id, timestamp=timestamp)
        self.T = Orientation()
        self.object_id = object_id
        self.update(properties, timestamp)

    def update(self, properties: dict, timestamp: datetime.datetime):
        """
        Updates the properties of the object.

        Args:
            properties (dict): The properties to update.
        """
        self.timestamp = timestamp
        self.properties = {**self.properties, **properties}

        for key, value in self.properties.items():

            if key == "T":

                for key, value in value.items():
                    setattr(self.T, str(key), _t_types[str(key)](value))
            elif key in _types:
                setattr(self, str(key), _types[str(key)](value))


# Do these once for performance #TODO figure out a cleaner home for these
_types = get_type_hints(ACMIObject)
_t_types = get_type_hints(Orientation)


class ACMIFileParser:

    def __init__(self, file_path: str | None = None):
        """
        Initialize an ACMIFileParser object.

        Args:
            file_path (str, optional): The path to the ACMI file. Defaults to None.
        """
        self.file_path = file_path
        self.global_obj = {}
        self.objects = {}
        self.reference_time: datetime.datetime = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
        self.relative_time = 0

    def parse_file(self):
        """
        Parses an entire ACMI file into self.objects.
        """
        if self.file_path is None:
            raise FileExistsError("No File given on init")

        with open(self.file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                self.parse_line(line)

    def get_time(self) -> datetime.datetime:
        """
        Returns the current time in the ACMI file.

        Returns:
            datetime.datetime: The current time in the ACMI file.
        """
        return self.reference_time + datetime.timedelta(seconds=self.relative_time)

    def get_action(self, line: str) -> str | None:
        """
        Returns the action in the ACMI file.

        Returns:
            list: The action in the ACMI file.
        """
        line = line.strip()
        if line.startswith('FileType'):
            return None

        if line.startswith('FileVersion'):
            return None

        if line.startswith('#'):
            return ACTION_TIME

        if line.startswith('-'):
            return ACTION_REMOVE

        parts = line.split(',')
        object_id = parts[0]
        if object_id == '0':
            return ACTION_GLOBAL

        return ACTION_UPDATE

    def parse_line(self, line: str) -> ACMIEntry | None:
        """
        Parses an ACMI line into an ACMIEntry.

        Args:
            line (str): The ACMI line to parse.

        Returns:
            ACMIEntry: The parsed ACMI line as an object.
        """
        line = line.strip()

        if line.startswith('FileType'):
            return None

        if line.startswith('FileVersion'):
            return None

        if line.startswith('#'):
            # Parse time frame
            time_frame = float(line[1:])
            self.relative_time = time_frame
            return ACMIEntry(ACTION_TIME, timestamp=self.get_time(), delta_time=time_frame)

        if line.startswith('-'):
            # Remove object from battlefield
            object_id = line[1:]
            return ACMIEntry(ACTION_REMOVE, timestamp=self.get_time(), object_id=object_id)

        else:

            # Parse object data
            parts = line.split(',')
            object_id = parts[0]
            if object_id == '0': object_id = "global"

            # Parse each key=value pair out of the ACMI object_id line
            properties = {}
            for prop in parts[1:]:
                try:
                    key, value = prop.split('=')
                except ValueError:
                    print(f"Caught ValueError {parts}")
                    break
                if key in "T":
                    position_vals = self.parse_t(value)
                    if position_vals is not None:
                        value = {key: val for key, val in position_vals.items() if val is not None}
                    else:
                        print(f"Invalid T value: {line}")
                        break

                properties[key] = value

            if object_id == "global":
                if "ReferenceTime" in properties:
                    # format 2024-6-9T00:00:00Z
                    self.reference_time = datetime.datetime.strptime(properties["ReferenceTime"], "%Y-%m-%dT%H:%M:%SZ")
                    self.reference_time = self.reference_time.replace(tzinfo=datetime.timezone.utc)
                return ACMIObject(ACTION_GLOBAL, object_id, properties, self.get_time())

            else:
                return ACMIObject(ACTION_UPDATE, object_id, properties, self.get_time())

    def parse_t(self, t: str) -> dict | None:
        """ 
        Parses the position information key=val pair into a dictionary.

        Args:
            t (str): The position information string.

        Returns:
            dict: The parsed position information as a dictionary.
        """
        data = t.split('|')
        num_pipes = t.count('|')

        if num_pipes == 2:
            # Simple objects in a spherical world
            return None

        if num_pipes == 4:
            # Simple objects from a flat world
            lon, lat, alt, u, v = map(lambda x: float(x.strip()) if x.strip() else None, data)
            return {"Longitude": lon, "Latitude": lat, "Altitude": alt, "U": u, "V": v}

        if num_pipes == 5:
            # Complex objects in a spherical world

            # START HACK FOR EXTRA PIPE BAR IN BULLSEYE
            #Todo remove when the extra pipe bar is removed
            print(f"FIX ME | Extra pipe bar in bullseye: {t}")
            lon, lat, alt, u, v, tmp = map(lambda x: float(x.strip()) if x.strip() else None, data)
            return {"Longitude": lon, "Latitude": lat, "Altitude": alt, "U": u, "V": v}

            #END HACK

            return None

        if num_pipes == 8:
            # Complex object from a flat world
            elements = map(lambda x: float(x.strip()) if x.strip() else None, data)
            lon, lat, alt, roll, pitch, yaw, u, v, heading = elements
            return {
                "Longitude": lon,
                "Latitude": lat,
                "Altitude": alt,
                "Roll": roll,
                "Pitch": pitch,
                "Yaw": yaw,
                "U": u,
                "V": v,
                "Heading": heading
            }

        return None  # Invalid format


if __name__ == "__main__":
    from pprint import pprint
    parser = ACMIFileParser("Data/test.txt")
    pprint(
        parser.parse_line(
            "9341,T=6.852304|7.270763|4572.13|-4.2|3.5|-161.8|701491.99|679328.81|-155.7,Health=1.00,Type=Air+FixedWing,Name=F-16CM-52,Pilot=Falcon42,Coalition=Bosnia,Color=Cyan,LockedTarget=0,FuelWeight=2704,AOA=3.3,AOS=0.0,IAS=188,CAS=188,Mach=0.72,LongitudinalGForce=-0.3,VerticalGForce=1.2,LateralGForce=0.0"
        ))
    pprint(
        parser.parse_line(
            "9337,T=6.850307|7.270096|4572.28|-0.0|3.0|-161.6|701287.54|679260.62|-155.4,Health=1.00,Type=Air+FixedWing,Name=F-16CM-52,Pilot=Briland,Coalition=Bosnia,Color=Cyan,LockedTarget=0,FuelWeight=2704,AOA=2.7,AOS=-0.0,IAS=188,CAS=188,Mach=0.72,LongitudinalGForce=-0.3,VerticalGForce=1.0,LateralGForce=0.0"
        ))
