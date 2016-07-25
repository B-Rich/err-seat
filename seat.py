import requests
from errbot import BotPlugin, botcmd, cmdfilter
import datetime

class Seat(BotPlugin):
    """Seat API to errbot interface"""

    def activate(self):
        super(Seat, self).activate()
        # populate all data at startup
        self.seat_headers = {'X-Token': self.config['SEAT_TOKEN'], 'Accept': 'application/json'}
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
            self._poller_check_pos_modules
        )

    ####################################################################################################################
    # Configuration
    def get_configuration_template(self):
        return {'SEAT_TOKEN': '<your_seat_token>', 'SEAT_URL': '<your_seat_url>', 'FUEL_THRESHOLD': '12',
                'REPORT_POS_CHAN': '<yourchannel>', 'REPORT_REINF_CHAN': '<yourchannel>'}

    ####################################################################################################################
    # Api Calls
    def _get_seat_all_corps(self):
        try:
            r = requests.get(self.config['SEAT_URL'] + "/corporation/all", headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_starbases(self, corpid):
        try:
            r = requests.get(self.config['SEAT_URL'] + "/corporation/starbases/" + str(corpid),
                             headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_pocos(self, corpid):
        try:
            r = requests.get(self.config['SEAT_URL'] + "/corporation/pocos/" + str(corpid), headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_pos_contents(self, corpid, posid):
        try:
            r = requests.get(self.config['SEAT_URL'] + "/corporation/starbases/" + str(corpid) + "/" + str(posid),
                             headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_posmod_contents(self, corpid, modid):
        try:
            r = requests.get(
                self.config['SEAT_URL'] + "/corporation/assets-contents/" + str(corpid) + "/" + str(modid),
                headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    ####################################################################################################################
    # Helpers

    ## Calculation
    def pos_fuel_hours_left(self, itemid):
        starbase = self['starbases'][itemid]
        hours_left = starbase['fuelBlocks'] / starbase['baseFuelUsage']
        return hours_left

    def pos_stront_hours_left(self, itemid):
        starbase = self['starbases'][itemid]
        hours_left = starbase['strontium'] / starbase['baseStrontUsage']
        return hours_left

    def mcheck_siphon(self, past_count, actual_count):
        if past_count == actual_count:
            return False
        elif past_count == actual_count + 100:
            return False
        else:
            return True


    ## Data Manipuation
    def add_starbase(self, corpid, corpticker, itemid, name, type, updated_at, onAggression, solarsystem, moon,
                     baseFuelUsage, fuelBaySize, fuelBlocks, baseStrontUsage, strontBaySize, strontium, state,
                     stateTimeStamp):
        # warning logic
        warn_fuel = True
        warn_reinf = True
        warn_stront = True
        warn_outdated = True
        warn_siphon = True
        starbasetmp = self['starbases'].get(itemid)
        if starbasetmp is not None:
            warn_fuel = starbasetmp['warn_fuel']
            warn_reinf = starbasetmp['warn_reinf']
            warn_stront = starbasetmp['warn_stront']
            warn_outdated = starbasetmp['warn_outdated']
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
            "warn_reinf": warn_reinf,
            "warn_stront": warn_stront,
            "warn_outdated": warn_outdated,
            "warn_siphon": warn_siphon,
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

    def add_module(self, moduleid, modulecontent):
        # warning logic
        warn_full = True
        moduletmp = self['modules'].get(moduleid)
        if moduletmp is not None:
            warn_full = moduletmp['warn_full']
        module = {
            "id": moduleid,
            "content": modulecontent,
            "warn_full": warn_full,
        }
        self.store_module(module)

    def store_module(self, module):
        modules = self.get('modules', {})
        modules[module['id']] = module
        self['modules'] = modules

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

    ## Silence Commands
    def pos_warn_fuel(self, posid, state):
        starbases = self['starbases']
        starbases[posid]['warn_fuel'] = state
        self['starbases'] = starbases

    def module_warn_full(self, moduleid, state):
        modules = self['modules']
        modules[moduleid]['warn_full'] = state
        self['modules'] = modules

    def pos_warn_stront(self, posid, state):
        starbases = self['starbases']
        starbases[posid]['warn_stront'] = state
        self['starbases'] = starbases

    def pos_warn_reinf(self, posid, state):
        starbases = self['starbases']
        starbases[posid]['warn_reinf'] = state
        self['starbases'] = starbases

    def pos_warn_siphon(self, posid, state):
        starbases = self['starbases']
        starbases[posid]['warn_siphon'] = state
        self['starbases'] = starbases

    ####################################################################################################################
    # poller functions
    def _poller_fetch_starbases(self):
        """Fetches all starbases"""
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
        """Fetches all pocos"""
        corplist = self._get_seat_all_corps()
        for corp in corplist:
            pocolist = self._get_seat_all_pocos(str(corp['corporationID']))
            for poco in pocolist:
                self.add_poco(itemid=poco['itemID'], corpticker=corp['ticker'], planetName=poco['planetName'],
                              planetTypeName=poco['planetTypeName'], reinforceHour=poco['reinforceHour'],
                              solarSystemName=poco['solarSystemName'])

    def _poller_check_pos(self, thresholdtmp=None):
        """Executes checks on the pos itself"""
        threshold = thresholdtmp if thresholdtmp else self.config['FUEL_THRESHOLD']
        for starbase in self.get_all_starbases():
            # check fuel
            fuel_left = self.pos_fuel_hours_left(starbase['id'])
            # check for outdated
            if starbase['outdated'] is True and (starbase['state'] == 4 or starbase['state'] == 3):
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Outdated**: %s - %s - %s is outdated, please check corp key" % (
                              starbase['moon'], starbase['type'], starbase['corp']))
                exit()
            elif int(fuel_left) < threshold and int(fuel_left) != 0 and starbase['warn_fuel'] is True:
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Fuel:** Tower is running out of fuel in %s hours - %s - %s - %s" % (
                              round(fuel_left), starbase['moon'], starbase['type'], starbase['corp'],))
                self.pos_warn_fuel(starbase['id'], False)
            # check reinforcement
            elif starbase['state'] == 3 and starbase['warn_reinf'] is True:
                self.send(self.build_identifier(self.config['REPORT_REINF_CHAN']),
                          "**Reinforced:** %s - %s - %s got reinforced. Timer: %s" % (
                              starbase['moon'], starbase['type'], starbase['corp'], starbase['stateTimeStamp']))
                self.pos_warn_reinf(starbase['id'], False)
            # check for empty stront
            if starbase['strontium'] == 0 and starbase['state'] == 4:
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s has no strontium." % (
                              starbase['moon'], starbase['type'], starbase['corp'], starbase['name']))
                self.pos_warn_reinf(starbase['posid'], True)
            ## clear warnings
            # assume refilled
            elif int(fuel_left) > threshold and starbase['warn_fuel'] is False:
                self.pos_warn_fuel(starbase['id'], True)
            # assume restronted
            elif starbase['strontium'] == 0 and starbase['warn_stront'] is False:
                self.pos_warn_stront(starbase['id'], True)

    def _poller_check_pos_modules(self):
        """Executes checks on pos modules"""
        for starbase in self.get_all_starbases():
            poscontent = self._get_seat_pos_contents(starbase['corpid'], starbase['id'])
            try:
                for module in poscontent['modules']:
                    # 14343 for silo, 17982 for coupling arrays
                    if module['detail']['typeID'] == 14343 or module['detail']['typeID'] == 17982:
                        m_id = module['detail']['itemID']
                        s_id = starbase['id']
                        m_capacity = module['detail']['capacity']
                        m_name = module['detail']['typeName']
                        m_location = module['detail']['mapName']
                        modulecontent = self._get_seat_posmod_contents(starbase['corpid'], m_id)
                        mc_amount = modulecontent[0]['quantity']
                        self.add_module(m_id, mc_amount)
                        stored_amount = self['modules'][m_id]['content']
                        # check siphon fml
                        if self.mcheck_siphon(stored_amount, mc_amount) and module['warn_siphon'] is True:
                            self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                                      "**Siphon:** Possible siphon detected: %s - %s - %s" % (
                                          starbase['moon'], starbase['type'], starbase['corp']))
                            self.pos_warn_siphon(s_id, False)
                        # check for full
                        elif mc_amount == m_capacity and module['warn_full'] is True:
                            self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                                      "**Full:** %s - %s - %s - %s is full" % (
                                          m_name, m_location, starbase['type'], starbase['corp'],))
                            self.module_warn_full(s_id, False)
                        # assume siphon killed
                        elif self.mcheck_siphon(stored_amount, mc_amount) is False and starbase['warn_siphon'] is False:
                            self.pos_warn_siphon(s_id, True)
                        # assume emptied
                        elif mc_amount != m_capacity and module['warn_full'] is False:
                            self.module_warn_full(s_id, True)
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
                    yield "**Location:** %s - %s **Type:** %s **Corp:** %s **Reinforcement**: set to %sh" % (
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
        results = 0
        for starbase in self.get_all_starbases():
            hours_left = self.pos_fuel_hours_left(starbase['id'])
            if int(hours_left) < int(args) and int(hours_left) != 0:
                results += 1
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s **Hours of fuel left:** %s" % (
                    starbase['moon'], starbase['type'], starbase['corp'], starbase['name'], round(hours_left))
            if results == 0:
                yield "Did not found any towers."
            else:
                yield "Found %s starbases total." % results

    @botcmd
    def pos_oos(self, msg, args):
        """Finds all towers that have no stront, Usage: !pos oos"""
        if args != '':
            yield 'Usage: !pos oos'
            return
        results = 0
        for starbase in self.get_all_starbases():
            if starbase['strontium'] == 0 and starbase['state'] == 4:
                results += 1
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s has no strontium." % (
                    starbase['moon'], starbase['type'], starbase['corp'], starbase['name'])
        if results == 0:
            yield "Did not found any towers without stront."
        else:
            yield "Found %s starbases total." % results

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

    ## Admin Commands
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
    def pos_triggerposcheck(self, msg, args):
        """Manually executes the checks on the pos itself"""
        self._poller_check_pos()
        return "Ran manual pos check."

    @botcmd(admin_only=True, hidden=True)
    def pos_triggerposmodcheck(self, msg, args):
        """Manually executes the checks on various posmodules"""
        self._poller_check_pos_modules()
        return "Ran manual pos module check."
