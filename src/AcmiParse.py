ACTION_UPDATE = "+"
ACTION_REMOVE = "-"
ACTION_TIME = "#"
ACTION_GLOBAL = "global"

class ACMIEntry:
    """
    Represents an entry in an ACMI (Air Combat Maneuvering Instrumentation) file.

    Attributes:
        action (str): The action performed in the entry.
        object_id (str): The ID of the object associated with the entry.
        timestamp (float): The timestamp of the entry.
    """

    def __init__(self, action: str, object_id: str = "", timestamp: float = 0.0):
        self.action = action
        self.object_id = object_id
        self.timestamp = timestamp
    
class ACMIObject (ACMIEntry):
    def __init__(self, action, object_id: str, properties: dict):
        """
        Initialize an ACMIEntry object.

        Args:
            object_id (str): The ID of the object.
            properties (dict): The properties of the object.
        """
        super().__init__(action, object_id)
        self.object_id = object_id
        self.properties = dict()
        self.AOA = 0.0
        self.AOS = 0.0
        self.CAS = 0.0
        self.Coalition = ""
        self.Color = ""
        self.FuelWeight = 0.0
        self.Health = 0.0
        self.IAS = 0.0
        self.LateralGForce = 0.0
        self.LockedTarget = 0
        self.LongitudinalGForce = 0.0
        self.Mach = 0.0
        self.Name = ""
        self.Pilot = ""
        self.T = {
            'Altitude': 0.0,
            'Heading': 0.0,
            'Latitude': 0.0,
            'Longitude': 0.0,
            'Pitch': 0.0,
            'Roll': 0.0,
            'U': 0.0,
            'V': 0.0,
            'Yaw': 0.0
        }
        self.Type = ""
        self.VerticalGForce = 0.0
        
        self.update(properties)
        
    def update(self, properties: dict):
        """
        Updates the properties of the object.

        Args:
            properties (dict): The properties to update.
        """
        self.properties = {**self.properties, **properties}
        
        for key, value in self.properties.items():
            setattr(self, str(key), value)
        
    def __str__(self):
        return f"ACMIEntry({self.object_id}, {self.properties})"
        

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

    def parse_line(self, line: str) -> ACMIEntry | None:
        """
        Parses an ACMI line into a dictionary.

        Args:
            line (str): The ACMI line to parse.

        Returns:
            dict: The parsed ACMI line as a dictionary.
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
            return ACMIEntry(ACTION_TIME, timestamp=time_frame)

        if line.startswith('-'):
            # Remove object from battlefield
            object_id = line[1:]
            return ACMIEntry(ACTION_REMOVE, object_id)

        else:
            # Parse object data
            parts = line.split(',')
            object_id = parts[0]
            if object_id == '0': object_id = "global"

            # TODO remove when we get the updated version of BMS that includes
            # U and V in all acmi messages, or finish lla_to_uv
            if line.count('|') < 8:
                return None

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

                properties[key] = value
            
            if object_id == "global":
                return ACMIObject(ACTION_GLOBAL, object_id, properties)
            
            else:
                return ACMIObject(ACTION_UPDATE, object_id, properties)

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
            return {
                "Longitude": lon,
                "Latitude": lat,
                "Altitude": alt,
                "U": u,
                "V": v
            }

        if num_pipes == 5:
            # Complex objects in a spherical world
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
    pprint(parser.parse_line("9341,T=6.852304|7.270763|4572.13|-4.2|3.5|-161.8|701491.99|679328.81|-155.7,Health=1.00,Type=Air+FixedWing,Name=F-16CM-52,Pilot=Falcon42,Coalition=Bosnia,Color=Cyan,LockedTarget=0,FuelWeight=2704,AOA=3.3,AOS=0.0,IAS=188,CAS=188,Mach=0.72,LongitudinalGForce=-0.3,VerticalGForce=1.2,LateralGForce=0.0"))
    pprint(parser.parse_line("9337,T=6.850307|7.270096|4572.28|-0.0|3.0|-161.6|701287.54|679260.62|-155.4,Health=1.00,Type=Air+FixedWing,Name=F-16CM-52,Pilot=Briland,Coalition=Bosnia,Color=Cyan,LockedTarget=0,FuelWeight=2704,AOA=2.7,AOS=-0.0,IAS=188,CAS=188,Mach=0.72,LongitudinalGForce=-0.3,VerticalGForce=1.0,LateralGForce=0.0"))
