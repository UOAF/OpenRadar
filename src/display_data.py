from game_state import GameState

class DisplayData:
    """
    Class of objects to display on the screen.
    """
    def __init__(self, gamestate: GameState):
        self.gamestate = gamestate
        self.annotations = []
        self.tracks = []
        
    def render(self):
        """
        Render the display data.
        """
        # for track in self.tracks:
        #     track.render()
            
        # for annotation in self.annotations:
        #     annotation.render()
        
    


