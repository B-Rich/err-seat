from errbot import BotPlugin, botcmd, cmdfilter
from models.seatdata import SeatData
from models.starbases import Module, Silo, Starbase


class Seat(BotPlugin):
    """Seat API to errbot interface"""

    def activate(self):
        super(Seat, self).activate()
        # populate all data at startup
        if SeatData.STORAGE_KEY in self:
            # Loading existing data
            self.seat_data = self[SeatData.STORAGE_KEY]
        else:
            # New/initial data structure
            self.seat_data = SeatData(self.config['SEAT_TOKEN'], self.config['SEAT_URL'])

        self.seat_data.fetch_starbases()
        self.seat_data.fetch_pocos()
        self.start_poller(
            1800,
            self.seat_data.fetch_starbases()
        )
        self.start_poller(
            1800,
            self.seat_data.fetch_pocos()
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
    # Helpers
    def _poller_check_pos(self, thresholdtmp=None):
        """Executes checks on the pos itself"""
        threshold = thresholdtmp if thresholdtmp else self.config['FUEL_THRESHOLD']
        for starbase in self.seat_data.get_all_starbases():
            # check fuel
            if starbase.check_fuel(threshold) and starbase.warn.fuel:
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Fuel:** Tower is running out of fuel in %s hours - %s - %s - %s | "
                          "Use *!pos silencefuel %s* to mute" % (
                              round(starbase.pos_fuel_hours_left()), starbase.moon, starbase.type, starbase.corp,
                              starbase.id,))
            # assume refilled
            elif starbase.check_refuelled():
                starbase.warn.fuel = True

            # check reinforcement
            if starbase.check_reinforced() and starbase.warn.reinf:
                self.send(self.build_identifier(self.config['REPORT_REINF_CHAN']),
                          "**Reinforced:** %s - %s - %s got reinforced. Timer: %s" % (
                              starbase.moon, starbase.type, starbase.corp, starbase.stateTimeStamp))
                # Only warn once
                starbase.warn.reinf = False
            # check for outdated
            if starbase.check_outdated():
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Outdated**: %s - %s - %s is outdated, please check corp key" % (
                              starbase.moon, starbase.type, starbase.corp))

            # check for empty stront
            if starbase.check_empty_stront() and starbase.warn.stront:
                self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                          "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s has no strontium." % (
                        starbase.moon, starbase.type, starbase.corp, starbase.name))
            # assume restronted
            elif starbase.check_stront_refuelled():
                starbase.warn.stront = True

        self.seat_data.trigger_save()  # TODO: This should be detected internally somehow

    def _poller_check_pos_modules(self):
        """Executes checks on pos modules"""
        for starbase in self.seat_data.get_all_starbases():
            poscontent = self.seat_data._get_seat_pos_contents(starbase.corp.id, starbase.id)  # TODO

            for module_json in poscontent['modules']:
                module = Module.factory(module_json)
                if type(module) is Silo:
                    module.set_contents(self.seat_data._get_seat_silo_contents(starbase.corp.id, module.itemID))  # TODO
                    # check for full
                    if module.silo_full() and starbase.warn.full:
                        self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                                  "**Full:** Silo/CouplingArray is full: %s - %s - %s"
                                  " | Use *!pos silencefull %s* to mute" % (
                                      starbase.moon, starbase.type, starbase.corp, starbase.id))
                    # assume emptied
                    elif module.silo_emptied() and not starbase.warn.full:
                        starbase.warn.full = True

        self.seat_data.trigger_save()  # TODO: This should be detected internally somehow

    ####################################################################################################################
    # bot commands
    @botcmd
    def pos_find(self, msg, args):
        """Finds all towers in given <system>, Usage !pos find <system>"""
        if args == '':
            yield 'Usage: !pos find <system>'
            return
        results = 0
        for starbase in self.seat_data.get_all_starbases():
            if starbase.solarsystem.lower() == args.lower():
                results += 1
                fuel_left = starbase.pos_fuel_hours_left()
                stront_left = starbase.pos_stront_hours_left()
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s " \
                      "**Fuel left**: %sh **Stront timer**: %sh" % (
                        starbase.moon, starbase.type, starbase.corp, starbase.name, round(fuel_left),
                        round(stront_left))
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
        for poco in self.seat_data.get_all_pocos():
            if poco.solarsystem.lower() == args.lower():
                results += 1
                yield "**Location:** %s - %s **Type:** %s **Corp:** %s **Reinforcement**: set to %sh" % (
                    poco.solarsystem, poco.planetName, poco.planetTypeName, poco.corp,
                    poco.reinforceHour)

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
        for starbase in self.seat_data.get_all_starbases():
            hours_left = starbase.pos_fuel_hours_left()
            if int(hours_left) < int(args) and int(hours_left) != 0:
                results += 1
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s **Hours of fuel left:** %s" % (
                    starbase.moon, starbase.type, starbase.corp, starbase.name, round(hours_left))
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
        for starbase in self.seat_data.get_all_starbases():
            if starbase.strontium == 0 and starbase.state == Starbase.STATE_ONLINE:
                results += 1
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s has no strontium." % (
                    starbase.moon, starbase.type, starbase.corp, starbase.name)
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
        for starbase in self.seat_data.get_all_starbases():
            if starbase.state == Starbase.STATE_ANCHORED or starbase.state == Starbase.STATE_UNANCHORED:
                yield "**Location:** %s **Type:** %s **Corp:** %s **Name:** %s " % (
                    starbase.moon, starbase.type, starbase.corp, starbase.name)

    @botcmd
    def pos_checksiphon(self, msg, args):
        """Locates possible siphons. Processing can take a while. Usage: !pos checksiphon"""
        if args != '':
            yield 'Usage: !pos checksiphon'
            return
        result = 0
        for starbase in self.seat_data.get_all_starbases():
            poscontent = self.seat_data._get_seat_pos_contents(starbase.corp.id, starbase.id)  # TODO

            for module_json in poscontent['modules']:
                module = Module.factory(module_json)
                # 14343 for silo, 17982 for coupling arrays
                if type(module) is Silo:
                    module.set_contents(self.seat_data._get_seat_silo_contents(starbase.corp.id, module.itemID))  # TODO
                    # check siphon
                    if module.has_siphon():
                        self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                                  "**Siphon:** Possible siphon detected: %s - %s - %s" % (
                                      starbase.moon, starbase.type, starbase.corp))
                        result += 1
        if result == 0:
            yield "Did not find any siphons."

    ## Silence Commands
    @botcmd
    def pos_silencefuel(self, msg, args):
        """Silences the out of fuel notification for a tower: Usage !pos silencefuel <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencefuel <posID>'
        starbase = self.seat_data.get_starbase_by_id(int(args))
        starbase.warn.fuel = False
        self.seat_data.trigger_save()  # TODO
        return "Silenced %s" % starbase.moon

    @botcmd
    def pos_silencefull(self, msg, args):
        """Silences notification if a silo/coupling array is full: Usage !pos silencefull <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencefull <posID>'
        starbase = self.seat_data.get_starbase_by_id(int(args))
        starbase.warn.full = False
        self.seat_data.trigger_save()  # TODO
        return "Silenced %s" % starbase.moon

    @botcmd
    def pos_silencestront(self, msg, args):
        """Silences notification for empty strontbays: Usage !pos silencestront <PosID>"""
        if args == '' or args.isdigit() is False:
            return 'Usage: !pos silencestront <posID>'
        starbase = self.seat_data.get_starbase_by_id(int(args))
        starbase.warn.stront = False
        self.seat_data.trigger_save()  # TODO
        return "Silenced %s" % starbase.moon

    ## Admin Commands
    @botcmd(admin_only=True)
    def pos_refetch(self, msg, args):
        """Refetches seat pos API data"""
        self.seat_data.fetch_starbases()
        return "Refetched seat pos data"

    @botcmd(admin_only=True)
    def poco_refetch(self, msg, args):
        """Refetches seat poco API data"""
        self.seat_data.fetch_pocos()
        return "Refetched seat poco data"

    @botcmd(admin_only=True, hidden=True)
    def pos_triggerposcheck(self, msg, args):
        """Manually executes the checks on the pos itself"""
        self._poller_check_pos()
        return "Ran manual pos check."

    @botcmd(admin_only=True, hidden=True)
    def pos_triggerposmodulecheck(self, msg, args):
        """Manually executes the checks on various posmodules"""
        self._poller_check_pos_modules()
        return "Ran manual pos module check."
