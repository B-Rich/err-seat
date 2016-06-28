import requests
from errbot import BotPlugin, botcmd
import datetime

########################################################################################################################
## Plugin Config
# url to your seat instance
seat_url = ''
# seat api token
seat_token = ''
# seat header (don't change)
seat_headers = {'X-Token': seat_token, 'Accept': 'application/json'}
# threshold before reporting out of fuel(hours)
fuel_threshold = 12
# reporting channels
report_pos_channel = '<channel for pos events, i.e. "#ops">'
report_reinf_channel = '<channel for reporting reinforcement, i.e. "#fc">'

class seat(BotPlugin):
    """Seat API to errbot interface"""

    def activate(self):
        super(seat, self).activate()
        # populate all data at startup
        self['starbases'] = {}
        self['pocos'] = {}
        self._poller_fetch_starbases()
        self._poller_fetch_pocos()
        self.start_poller(
            1800,
            self._poller_fetch_starbases
        )
        self.start_poller(
            1800,
            self._poller_fetch_pocos
        )
        self.start_poller(
            3600,
            self._poller_check_pos
        )
        self.start_poller(
            3600,
            self._poller_check_silos
        )
    ####################################################################################################################
    # Helpers
    def _get_seat_all_corps(self):
        try:
            r = requests.get(seat_url + "/corporation/all", headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_starbases(self, corpid):
        try:
            r = requests.get(seat_url + "/corporation/starbases/" + str(corpid), headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_assets(self, corpid):
        try:
            r = requests.get(seat_url + "/corporation/assets/" + str(corpid), headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_pos_contents(self, corpid, posid):
        try:
            r = requests.get(seat_url + "/corporation/starbases/" + str(corpid) + "/" + str(posid),
                             headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_silo_contents(self, corpid, siloid):
        try:
            r = requests.get(seat_url + "/corporation/assets-contents/" + str(corpid) + "/" + str(siloid),
                             headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_pocos(self, corpid):
        try:
            r = requests.get(seat_url + "/corporation/pocos/" + str(corpid), headers=seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def pos_fuel_hours_left(self, itemid):
        starbase = self['starbases'][itemid]
        hours_left = starbase['fuelBlocks'] / starbase['baseFuelUsage']
        return hours_left

    def pos_stront_hours_left(self, itemid):
        starbase = self['starbases'][itemid]
        hours_left = starbase['strontium'] / starbase['baseStrontUsage']
        return hours_left

    def add_starbase(self, corpid, corpticker, itemid, name, type, updated_at, onAggression, solarsystem, moon,
                     baseFuelUsage, fuelBaySize, fuelBlocks, baseStrontUsage, strontBaySize, strontium, state,
                     stateTimeStamp):
        # warning logic
        warn_fuel = True
        warn_reinf = True
        warn_full = True
        warn_siphon = True
        starbasetmp = self['starbases'].get(itemid)
        if starbasetmp is not None:
            warn_fuel = starbasetmp['warn_fuel']
            warn_reinf = starbasetmp['warn_reinf']
            warn_full = starbasetmp['warn_full']
            warn_siphon = starbasetmp['warn_siphon']
        # check if data is outdated
        outdated = False
        postime = datetime.datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
        if postime < datetime.datetime.utcnow() - datetime.timedelta(hours=12):
            outdated = True
        starbase = {
            "id": itemid,
            "corpid": corpid,
            "corp": corpticker,
            "name": name,
            "type": type,
            "updated_at": updated_at,
            "onAggression": onAggression,
            "solarsystem": solarsystem,
            "moon": moon,
            "baseFuelUsage": baseFuelUsage,
            "fuelBaySize": fuelBaySize,
            "fuelBlocks": fuelBlocks,
            "baseStrontUsage": baseStrontUsage,
            "strontBaySize": strontBaySize,
            "strontium": strontium,
            "state": state,
            "stateTimeStamp": stateTimeStamp,
            "warn_fuel": warn_fuel,
            "warn_full": warn_full,
            "warn_siphon": warn_siphon,
            "warn_reinf": warn_reinf,
            "outdated": outdated,
        }
        self.store_starbase(starbase)

    def add_poco(self, itemid, corpticker, planetName, planetTypeName, reinforceHour, solarSystemName):
        poco = {
            "id": itemid,
            "corp": corpticker,
            "planetName": planetName,
            "planetTypeName": planetTypeName,
            "reinforceHour": reinforceHour,
            "solarsystem": solarSystemName,
        }
        self.store_poco(poco)

    def store_poco(self, poco):
        pocos = self.get('pocos', {})
        pocos[poco['id']] = poco
        self['pocos'] = pocos

    def store_starbase(self, starbase):
        starbases = self.get('starbases', {})
        starbases[starbase['id']] = starbase
        self['starbases'] = starbases

    def delete_starbase(self, starbaseid):
        starbases = self.get('starbases', {})
        del starbases[starbaseid]
        self['starbases'] = starbases

    def get_all_starbases(self):
        return self.get('starbases', {}).values()

    def get_all_pocos(self):
        return self.get('pocos', {}).values()

    ####################################################################################################################
    # poller functions
    def _poller_fetch_starbases(self):
        corplist = self._get_seat_all_corps()
        for corp in corplist:
            starbaselist = self._get_seat_all_starbases(str(corp['corporationID']))
            for starbase in starbaselist:
                self.add_starbase(itemid=starbase['itemID'], corpid=corp['corporationID'], corpticker=corp['ticker'],
                                  name=starbase['starbaseName'],
                                  type=starbase['starbaseTypeName'], updated_at=starbase['updated_at'],
                                  onAggression=starbase['onAggression'],
                                  solarsystem=starbase['solarSystemName'], moon=starbase['moonName'],
                                  baseFuelUsage=starbase['baseFuelUsage'], fuelBaySize=starbase['fuelBaySize'],
                                  fuelBlocks=starbase['fuelBlocks'], baseStrontUsage=starbase['baseStrontUsage'],
                                  strontBaySize=starbase['strontBaySize'], strontium=starbase['strontium'],
                                  state=starbase['state'], stateTimeStamp=starbase['stateTimeStamp'])

    def _poller_fetch_pocos(self):
        corplist = self._get_seat_all_corps()
        for corp in corplist:
            pocolist = self._get_seat_all_pocos(str(corp['corporationID']))
            for poco in pocolist:
                self.add_poco(itemid=poco['itemID'], corpticker=corp['ticker'], planetName=poco['planetName'],
                              planetTypeName=poco['planetTypeName'], reinforceHour=poco['reinforceHour'],
                              solarSystemName=poco['solarSystemName'])

    def _poller_check_pos(self, threshold=fuel_threshold):
        for starbase in self.get_all_starbases():
            # check fuelage
            fuel_left = self.pos_fuel_hours_left(starbase['id'])  #
            if int(fuel_left) < threshold and int(fuel_left) != 0 and starbase['warn_fuel'] is True:
                self.send(self.build_identifier(report_pos_channel),
                          "**Fuel:** Tower is running out of fuel in %s hours - %s - %s - %s | Use *!pos silencefuel %s* to mute" % (
                              round(fuel_left), starbase['moon'], starbase['type'], starbase['corp'], starbase['id'],))
            # assume refilled
            elif int(fuel_left) > threshold and starbase['warn_fuel'] is False:
                starbases = self['starbases']
                starbases[starbase['id']]['warn_fuel'] = True
                self['starbases'] = starbases
            # check reinforment
            elif starbase['state'] == 3 and starbase['warn_reinf'] is True:
                self.send(self.build_identifier(report_reinf_channel),
                          "**Reinforced:** %s - %s - %s got reinforced. Timer: %s" % (
                              starbase['moon'], starbase['type'], starbase['corp'], starbase['stateTimeStamp']))
                starbases = self['starbases']
                starbases[starbase['id']]['warn_reinf'] = False
                self['starbases'] = starbases
            # check for outdated while ignoring offline/anchored
            elif starbase['outdated'] is True and (starbase['state'] == 4 or starbase['state'] == 3):
                self.send(self.build_identifier(report_pos_channel),
                          "**Outdated**: %s - %s - %s is outdated, please check corp key" % (
                          starbase['moon'], starbase['type'], starbase['corp']))

    def _poller_check_silos(self):
        for starbase in self.get_all_starbases():
            poscontent = self._get_seat_pos_contents(starbase['corpid'], starbase['id'])
            try:
                for module in poscontent['modules']:
                    # 14343 for silo, 17982 for coupling
                    if module['detail']['typeID'] == 14343 or module['detail']['typeID'] == 17982:
                        modulecontent = self._get_seat_silo_contents(starbase['corpid'], module['detail']['itemID'])
                        # check siphon
                        if modulecontent[0]['quantity'] % 100 != 0 and starbase['warn_siphon'] is True:
                            self.send(self.build_identifier(report_pos_channel),
                                      "**Siphon:** Possible siphon detected: %s - %s - %s | Use *!pos silencesiphon %s* to mute" % (
                                          starbase['moon'], starbase['type'], starbase['corp'],
                                          starbase['id']))
                        # check for full
                        elif modulecontent[0]['quantity'] == module['detail']['capacity'] and starbase[
                            'warn_full'] is True:
                            self.send(self.build_identifier(report_pos_channel),
                                      "**Full:** Silo/CouplingArray is full: %s - %s - %s | Use *!pos silencefull %s* to mute" % (
                                          starbase['moon'], starbase['type'], starbase['corp'],
                                          starbase['id']))
                        # assume emptied
                        elif modulecontent[0]['quantity'] != module['detail']['capacity'] and starbase[
                            'warn_full'] is False:
                            starbases = self['starbases']
                            starbases[starbase['id']]['warn_full'] = True
                            self['starbases'] = starbases
                        # assume siphon killed
                        elif modulecontent[0]['quantity'] % 100 == 0 and starbase['warn_siphon'] is False:
                            starbases = self['starbases']
                            starbases[starbase['id']]['warn_siphon'] = True
                            self['starbases'] = starbases
            except:
                pass

    ####################################################################################################################
    # bot commands
    @botcmd
    def pos_find(self, msg, args):
        """Finds all towers in given <system>, Usage !pos find <system>"""
        if args == '':
            yield 'Usage: !pos find <system>'
            return
        results = 0
        for starbase in self.get_all_starbases():
            try:
                if starbase['solarsystem'].lower() == args.lower():
                    results += 1
                    fuel_left = self.pos_fuel_hours_left(starbase['id'])
                    stront_left = self.pos_stront_hours_left(starbase['id'])
                    yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s **Fuel left**: %sh **Stront timer**: %sh" % (
                        starbase['moon'], starbase['type'], starbase['corp'], starbase['name'], round(fuel_left),
                        round(stront_left))
            except:
                pass
        if results == 0:
            yield "There are no starbases in %s" % args
        else:
            yield "Found %s starbases total." % results

    @botcmd
    def poco_find(self, msg, args):
        """Finds all pocos in given <system>, Usage !poco find <system>"""
        if args == '':
            yield 'Usage: !poco find <system>'
            return
        results = 0
        for poco in self.get_all_pocos():
            try:
                if poco['solarsystem'].lower() == args.lower():
                    results += 1
                    yield "**Location:** %s - %s **Type:** %s **Corp:** %s **Reinforment**: set to %sh" % (
                        poco['solarsystem'], poco['planetName'], poco['planetTypeName'], poco['corp'],
                        poco['reinforceHour'])
            except:
                pass
        if results == 0:
            yield "There are no pocos in %s" % args
        else:
            yield "Found %s pocos total." % results

    @botcmd
    def pos_oof(self, msg, args):
        """Finds all towers that will be running out of fuel in the given timeframe, Usage: !pos oof <hours>"""
        if args == '' or args.isdigit() is False:
            yield 'Usage: !pos oof <hours>'
            return
        for starbase in self.get_all_starbases():
            hours_left = self.pos_fuel_hours_left(starbase['id'])
            if int(hours_left) < int(args) and int(hours_left) != 0:
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s **Hours of fuel left:** %s" % (
                    starbase['moon'], starbase['type'], starbase['corp'], starbase['name'], round(hours_left))

    @botcmd
    def pos_offline(self, msg, args):
        """Finds all offline towers, Usage: !pos offline"""
        if args != '':
            yield 'Usage: !pos offline'
            return
        for starbase in self.get_all_starbases():
            if starbase['state'] == 1 or starbase['state'] == 0:
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s " % (
                    starbase['moon'], starbase['type'], starbase['corp'], starbase['name'])

    @botcmd
    def pos_silencefuel(self, msg, args):
        """Silences the out of fuel notification for a tower: Usage !pos silencefuel <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencefuel <posID>'
        args = int(args)
        starbases = self['starbases']
        starbases[args]['warn_fuel'] = False
        self['starbases'] = starbases
        return "Silenced %s" % starbases[args]['moon']

    @botcmd
    def pos_silencesiphon(self, msg, args):
        """Silences the siphon notification for a tower: Usage !pos silencesiphon <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencesiphon <posID>'
        args = int(args)
        starbases = self['starbases']
        starbases[args]['warn_siphon'] = False
        self['starbases'] = starbases
        return "Silenced %s" % starbases[args]['moon']

    @botcmd
    def pos_silencefull(self, msg, args):
        """Silences notification if a silo/coupling array is full: Usage !pos silencefull <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencefull <posID>'
        args = int(args)
        starbases = self['starbases']
        starbases[args]['warn_full'] = False
        self['starbases'] = starbases
        return "Silenced %s" % starbases[args]['moon']

    @botcmd(admin_only=True)
    def pos_refetch(self, msg, args):
        """Refetches seat pos API data"""
        self._poller_fetch_starbases()
        return "Refetched seat pos data"

    @botcmd(admin_only=True)
    def poco_refetch(self, msg, args):
        """Refetches seat poco API data"""
        self._poller_fetch_pocos()
        return "Refetched seat poco data"

    @botcmd(admin_only=True, hidden=True)
    def pos_triggerfuelcheck(self, msg, args):
        """Manually executes the scheduled fuel / reinforcement check"""
        if args == '' or args.isdigit() is False:
            args = fuel_threshold
        self._poller_check_pos(int(args))
        return "Ran manual pos check with %s hours." % args

    @botcmd(admin_only=True, hidden=True)
    def pos_triggersilocheck(self, msg, args):
        """Manually executes the scheduled silo check"""
        if args == '' or args.isdigit() is False:
            args = fuel_threshold
        self._poller_check_silos()
        return "Ran manual silo check."
