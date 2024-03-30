# Balkans
# <West>11</West>
# <East>21</East>
# <South>36.625</South>
# <North>46.64</North>

class ACMIFileParser:
    def __init__(self, file_path: str=None):
        self.file_path = file_path
        self.global_obj = {}
        self.objects = {}
        self.relative_time = 0

    def parse_file(self):
        """ Parses an entire acmi file in self.file_path into self.objects
            TODO Refactor, non-func
        """

        if self.file_path is None:
            raise FileExistsError("No File given on init")
        
        with open(self.file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                self.parse_line(line)

    def parse_line(self, line: str) -> dict:
        """ Parses an Acmi line into a dict
            output dict is one of:
                '#': Timestamp
                '-': object_id
                'object_id': dict{}
                
            returns None if line is to be skipped
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
            return {"#": time_frame}

        if line.startswith('-'):
            # Remove object from battlefield
            object_id = line[1:]
            return {'-': object_id}

        else:
            # Parse object data
            parts = line.split(',')
            object_id = parts[0]
            if object_id is '0': object_id = "global"

            # TODO remove when we get the updated version of BMS that includes
            # U and V in all acmi messages, or finish lla_to_uv
            if line.count('|') < 8:
                return None

            # Parse each key=value pair out of the ACMI object_id line
            properties = {}
            for prop in parts[1:]:
                key, value = prop.split('=')
                if key in "T":
                    position_vals = self.parse_t(value)
                    value = {key: val for key, val in position_vals.items() if val is not None}
                    
                properties[key] = value
                
            return {object_id: properties}

            # except:
            #     print("Exception Line: ", line)

    def parse_t(self, t: str) -> dict:
        """ Parses the position information key=val pair into a dictionary
        """
        data = t.split('|')
        num_pipes = t.count('|')
        
        if num_pipes == 2:
            # Simple objects in a spherical world
            # long, lat, alt = map(lambda x: float(x.strip()) if x.strip() else None, data)
            # return {
            #     "Longitude": long,
            #     "Latitude": lat,
            #     "Altitude": alt
            # }
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


    # def loadAcmiold(self):

    #     if fname:
    #         print(fname)

    #         parser = ACMIFileParser(fname) # TODO do this somewhere smarter
    #         parser.parse_file()


    #         for obj_id, obj in parser.objects.items():
    #             # print(obj_id, ", ", object)
    #             if "Type" not in obj.keys() or not "Ground" in obj["Type"]:
    #                 print(obj_id, ", ", obj)
    #                 aircraft_id = obj_id
    #                 pos_ux = float(obj["T"]["U"])
    #                 pos_vy = float(obj["T"]["V"])

# Another hint if you are converting BMS objective X /Y which are between 0-1023 (km) the conversion for km to feet is best used 
# with 3279.98 ft per km insteed of RL 3280.84 ft per km (maybe 3281.58153320)

    #                 theatre_size_km = 1024 # TODO move out
    #                 Theater_max_meter = theatre_size_km * 1000

    #                 pixel_pos_x = pos_ux / Theater_max_meter * radar_map_size_x
    #                 pixel_pos_y = radar_map_size_y - pos_vy / Theater_max_meter * radar_map_size_y
    #                 # Draw aircraft on canvas

    #                 self.map.draw_aircontact(pixel_pos_x, pixel_pos_y)
    #                 print("Drawing:" ,pixel_pos_x,", ",pixel_pos_y)

    #     print(parser.removed_objects, ", ", parser.added_objects)
    