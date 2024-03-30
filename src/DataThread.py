import threading
import queue
import time

from PyQt6.QtCore import pyqtSignal, QThread

from AcmiParse import ACMIFileParser

SHOWN_OBJECT_CLASSES = ("Aircraft")
HIDDEN_OBJECT_CLASSES = ("Static", "Vehicle")

class DataThread(QThread):
    object_updates = pyqtSignal(dict)
    object_removals = pyqtSignal(str)

    def __init__(self, queue: queue.Queue) -> None:
        super(DataThread, self).__init__()
        self._queue = queue
        self.parser = ACMIFileParser()
        self.state = {}
        self.global_vars = {}

    def run(self):
        import pydevd;pydevd.settrace(suspend=False) # Register QThread for python debugger
        while True:

            line = self._queue.get()
            if line is None: break
            acmi_obj = self.parser.parse_line(line)
            if acmi_obj is None: continue

            object_key = list(acmi_obj.keys())[0]

            if object_key in ("-"):
                self.object_removals.emit(acmi_obj["-"])
                del self.state[object_key]
            elif object_key in ("#"):
                self.object_updates.emit(self.state)
            elif object_key in ("global"):
                self.global_vars = self.global_vars | acmi_obj["global"]
            else:
                self.update_object(acmi_obj)
            
    def update_object(self, object_next: dict) -> None:
        """
        Merges the object dict between last state and this state
        This is needed because the new state is not guaranteed to have position values in all fields 
        if there is no change
        """
        # If this is a new object_id simply add it
        object_id = list(object_next.keys())[0]
        if object_id not in self.state:
            if not any(clas in object_next[object_id].get("Type", "") for clas in HIDDEN_OBJECT_CLASSES):
                self.state[object_id] = object_next[object_id]
            return
        
        # Filter and merge new dictionary over old dictionary
        next_properties = {key: val for key, val in object_next[object_id].items() if val is not None}
        object_last = self.state[object_id]
        out_dict = object_last | next_properties
        out_dict["T"] = object_last["T"] | {key: val for key, val in next_properties["T"].items() if val is not None}
        
        self.state[object_id] = out_dict
        
# Testing
if __name__ == '__main__':

    q = queue.Queue()
    test = DataThread(q)
    test.state = { "123": {"T": {"lat":1,"lon":1,"alt":1}, "key": 12},
                   "124": {"T": {"lat":1,"lon":1,"alt":1}, "key": 12}
    }
    newdict = {"123": {"T": {"lat":2,"lon":2, "alt":None}, "obj": 11}}
    test.update_object(newdict)
    print(test.state)