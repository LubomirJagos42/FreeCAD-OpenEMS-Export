from .SettingsItem import SettingsItem

class BoundaryConditionSettingsItem(SettingsItem):
    def __init__(self, name="", type="", customType=""):
        self.name = name
        self.type = type
        self.customType = customType

        return

    def getName(self):
        return self.name

    def getType(self):
        if self.type == "custom":
            return self.customType
        else:
            return self.type
