import threading
import queue
import time
from PyQt6.QtCore import pyqtSignal

class DataThread(threading.Thread):

    def __init__(self, queue: queue.Queue) -> None:
        super(DataThread, self).__init__()
        self._queue = queue
        self.signal = pyqtSignal(str, name="Acmi Data Signal")

    def run(self):

        time.sleep(5)
        self.signal.emit("Message from worker thread")


        # while True:

        #     line = self._queue.get()
        #     if line is None: break




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
    