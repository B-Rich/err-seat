
class Poco:
    def __init__(self, poco, corp):
        self.id = poco['itemID']
        self.corp = corp
        self.planetName = poco['planetName']
        self.planetTypeName = poco['planetTypeName']
        self.reinforceHour = poco['reinforceHour']
        self.solarsystem = poco['solarSystemName']

    @property
    def corpticker(self):
        return self.corp.ticker
