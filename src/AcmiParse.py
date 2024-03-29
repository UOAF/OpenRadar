# Balkans
# <West>11</West>
# <East>21</East>
# <South>36.625</South>
# <North>46.64</North>

class ACMIFileParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.global_obj= {}
        self.objects = {}
        self.removed_objects = 0
        self.added_objects = 0
        print("Init Parser")

    def parse_file(self):
        """ Parses an entire acmi file in self.file_path into self.objects
        """
        print("Parsing ", self.file_path)
        with open(self.file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                self.parse_line(line)

    def parse_line(self, line: str):
        """ Parses an Acmi line into self.objects
        """
        line = line.strip()
        if line.startswith('FileType'):
            pass
        elif line.startswith('FileVersion'):
            pass
        elif line.startswith('#'):
            # Parse time frame
            time_frame = float(line[1:])
        elif line.startswith('-'):
            # Remove object from battlefield
            object_id = line[1:]
            if object_id in self.objects:
                del self.objects[object_id]

            self.removed_objects += 1
        else:
            # Parse object data
            parts = line.split(',')
            object_id = parts[0]

            if object_id is "0":
                for prop in parts[1:]:
                    key, value = prop.split('=')
                    self.global_obj[key] = value
                return
            # TODO remove when we get the updated version of BMS that includes
            # U and V in all acmi messages
            if line.count('|') < 8:
                return
            if not object_id in self.objects:
                self.objects[object_id] = {}
                self.added_objects += 1

            for prop in parts[1:]:
                key, value = prop.split('=')
                if key in "T":
                    value = self.parse_t(value)
                self.objects[object_id][key] = value
            # except:
            #     print("Exception Line: ", line)

    def parse_t(self, t: str) -> dict:
        """ Parses the position information key=val pair into a dictionary
        """
        data = t.split('|')
        num_pipes = t.count('|')

        if num_pipes == 2:
            # Simple objects in a spherical world
            # long, lat, alt = map(lambda x: float(x.strip()) if x.strip() else None, components)
            return None
            # return {
            #     "Longitude": long,
            #     "Latitude": lat,
            #     "Altitude": alt
            # }

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
            # elements = map(lambda x: float(x.strip()) if x.strip() else None, data)
            # lon, lat, alt, roll, pitch, yaw = elements
            return None
            # return {
            #     "Longitude": longitude,
            #     "Latitude": latitude,
            #     "Altitude": altitude,
            #     "Roll": roll,
            #     "Pitch": pitch,
            #     "Yaw": yaw
            # }
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
