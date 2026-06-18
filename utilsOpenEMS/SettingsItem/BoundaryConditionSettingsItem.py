from .SettingsItem import SettingsItem

class BoundaryConditionSettingsItem(SettingsItem):
    def __init__(
        self,
        name="",
        type="",
        customType="",
        surfaceImpedance={"material":None, "conductance":0.0, "roughness":0.0, "roughnessUnits":"nm", "thickness":0.0, "thicknessUnits":"um"},
        thinConductor={"material":None, "conductance":0.0, "roughness":0.0, "roughnessUnits":"nm", "thickness":0.0, "thicknessUnits":"um"}
    ):
        self.name = name
        self.type = type
        self.customType = customType
        self.surfaceImpedance = surfaceImpedance
        self.thinConductor = thinConductor

        return

    def getName(self):
        return self.name

    def getType(self):
        if self.type == "custom":
            return self.customType
        else:
            return self.type
