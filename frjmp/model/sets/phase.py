from frjmp.model.sets.need import Need


class Phase:
    def __init__(self, name: str, need: Need):
        self.name = name
        self.required_need = need

    def __repr__(self):
        return f"Phase {self.name}"
