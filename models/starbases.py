import datetime


class Starbase:

    STATE_UNANCHORED = 0
    STATE_ANCHORED = 1
    STATE_ONLINING = 2
    STATE_REINFORCED = 3
    STATE_ONLINE = 4

    def __init__(self, starbase, corp):
        """
        :param starbase: dict JSON
        :param corp: Corp object
        """
        self.id = starbase['itemID']
        self.corp = corp
        self.name = starbase['starbaseName']
        self.type = starbase['starbaseTypeName']
        self.updated_at = starbase['updated_at']
        self.onAggression = starbase['onAggression']
        self.solarsystem = starbase['solarSystemName']
        self.moon = starbase['moonName']
        self.baseFuelUsage = starbase['baseFuelUsage']
        self.fuelBaySize = starbase['fuelBaySize']
        self.fuelBlocks = starbase['fuelBlocks']
        self.baseStrontUsage = starbase['baseStrontUsage']
        self.strontBaySize = starbase['strontBaySize']
        self.strontium = starbase['strontium']
        self.state = starbase['state']
        self.stateTimeStamp = starbase['stateTimeStamp']
        self.warn = StarbaseWarn()  # Allows us to easily swap this out if the starbase exists
        self.outdated = False

        # check if data is outdated
        postime = datetime.datetime.strptime(self.updated_at, "%Y-%m-%d %H:%M:%S")
        if postime < datetime.datetime.utcnow() - datetime.timedelta(hours=12):
            self.outdated = True

    def pos_fuel_hours_left(self):
        hours_left = self.fuelBlocks / self.baseFuelUsage
        return hours_left

    def pos_stront_hours_left(self):
        hours_left = self.strontium / self.baseStrontUsage
        return hours_left

    def check_fuel(self, threshold=24):
        """
        Check fuel remaining in starbase
        :param threshold: int Hours of fuel left to alert on
        :return: bool True if the threshold is met, False otherwise
        """
        fuel_left = self.pos_fuel_hours_left()
        return int(fuel_left) < threshold and int(fuel_left) != 0

    def check_reinforced(self):
        """
        Check if a starbase is in reinforced mode
        :return: bool True if reinforced, False otherwise
        """
        return self.state == 3

    def check_outdated(self):
        return self.outdated and (self.state == 4 or self.state == 3)

    def check_empty_stront(self):
        return self.strontium == 0 and self.state == 4

    def check_stront_refuelled(self):
        # TODO: ??? I dont know if this makes sense with the data
        return self.strontium == 0

    def check_refuelled(self, threshold=24):
        return int(self.pos_stront_hours_left()) > threshold


class StarbaseWarn:
    def __init__(self):
        self.fuel = True
        self.full = True
        self.reinf = True
        self.stront = True


class Module:
    """
    Any POS modules
    """
    def __init__(self, module):
        self.typeID = module['typeID']
        self.itemID = module['itemID']
        self.capacity = module['capacity']

    @classmethod
    def factory(cls, module):
        if module['detail']['typeID'] == 14343 or module['detail']['typeID'] == 17982:
            # Silo/CouplingArray
            return Silo(module)
        else:
            return Module(module)


class Silo(Module):
    """
    Silo or CouplingArray
    """
    def __init__(self, module):
        super().__init__(module)
        self.quantity = 0

    def set_contents(self, contents):
        self.quantity = contents[0]['quantity']

    def silo_full(self):
        return self.quantity >= self.capacity

    def silo_emptied(self):
        return self.quantity < self.capacity

    def has_siphon(self):
        return self.quantity % 100 != 0
