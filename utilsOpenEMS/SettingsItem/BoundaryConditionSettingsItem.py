from .SettingsItem import SettingsItem

class BoundaryConditionSettingsItem(SettingsItem):
    def __init__(self, name="", type=""):
        self.name = name
        self.type = type

        return
