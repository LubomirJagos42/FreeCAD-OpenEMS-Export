import json
from .SettingsItem import SettingsItem

# Excitation settings, for input power where energy is floating into model
#   Sinusodial - input port is excitated by sinusodial electric field
#   Gaussian   - gaussian impulse at input port
#   Custom     - user has to define function of electric field at input port
#

class ExcitationSettingsItem(SettingsItem):
    def __init__(self, name="", type="", sinusodial=None, gaussian=None, custom=None, dirac=None, step=None, units = "Hz"):
        super().__init__(name=name, type=type, priority=0)
        self.sinusodial = {'f0': 0} if sinusodial is None else sinusodial
        self.gaussian = {'f0': 0, 'fc': 0} if gaussian is None else gaussian
        self.custom = {'functionStr': '0', 'f0': 0} if custom is None else custom
        self.step = {'fm': '0'} if step is None else step
        self.dirac = {'fm': '0'} if dirac is None else dirac
        self.units = units

    def __str__(self):
        return f'''name={self.name}
type={self.type}
sinusodial={json.dumps(self.sinusodial)}
gaussian={json.dumps(self.gaussian)}
step={json.dumps(self.step)}
dirac={json.dumps(self.dirac)}
custom={json.dumps(self.custom)}
units={self.units}'''

