class AircraftModel:
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Aircraft:
    def __init__(self, name: str, model: AircraftModel):
        self.name = name
        self.model = model

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
