from typing import Dict


class CoalitionManager:

    def __init__(self):
        # country -> "friendly" | "neutral" | "hostile"
        self._relations: Dict[str, str] = {}

    # ----------------------------
    # Relation Handling
    # ----------------------------

    def set_relation(self, country: str, relation: str):
        self._relations[country] = relation

    def get_relation(self, country: str) -> str:
        return self._relations.get(country, "neutral")

    # ----------------------------
    # Persistence (Optional But Recommended)
    # ----------------------------
    
coalition_manager = CoalitionManager()