import requests
from models.eveentities import Corp
from models.starbases import Starbase, Module
from models.pocos import Poco


class SeatData:

    STORAGE_KEY = 'seat_data'

    def __init__(self, seat_token, seat_url):
        self.seat_token = seat_token
        self.seat_url = seat_url

        self.starbases = {}
        self.pocos = {}

    @property
    def seat_headers(self):
        return {'X-Token': self.seat_token, 'Accept': 'application/json'}


    def trigger_save(self):
        pass

    ####################################################################################################################
    # poller functions
    def fetch_starbases(self):
        """Fetches all starbases"""
        corplist = self._get_seat_all_corps()
        for corp_json in corplist:
            corp = Corp(corp_json)
            starbaselist = self._get_seat_all_starbases(corp.corporationID)
            for starbase_json in starbaselist:
                self.add_starbase(Starbase(starbase_json, corp))

    def fetch_pocos(self):
        """Fetches all pocos"""
        corplist = self._get_seat_all_corps()
        for corp_json in corplist:
            corp = Corp(corp_json)
            pocolist = self._get_seat_all_pocos(corp.corporationID)
            for poco_json in pocolist:
                self.add_poco(Poco(poco_json, corp))

    ####################################################################################################################
    # Api Calls
    def _get_seat_all_corps(self):
        try:
            r = requests.get("{0}/corporation/all".format(self.seat_url), headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_starbases(self, corpid: int):
        try:
            r = requests.get("{0}/corporation/starbases/{1}".format(self.seat_url, corpid),
                             headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_all_pocos(self, corpid: int):
        try:
            r = requests.get("{0}/corporation/pocos/{1}".format(self.seat_url, corpid), headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_pos_contents(self, corpid, posid):
        try:
            r = requests.get("{0}/corporation/starbases/{1}/{2}".format(self.seat_url, corpid, posid),
                             headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    def _get_seat_silo_contents(self, corpid, siloid):
        try:
            r = requests.get("{0}/corporation/assets-contents/{1}/{2}".format(self.seat_url, corpid, siloid),
                             headers=self.seat_headers)
            return r.json()
        except requests.exceptions.RequestException as e:
            print(e)

    ####################################################################################################################
    # Helpers
    def add_starbase(self, starbase):
        """
        Add a starbase
        :param starbase: Starbase object
        :return:
        """
        starbasetmp = self.starbases.get(starbase.id)
        if starbasetmp is not None:
            starbase.warn = starbasetmp.warn
        self.store_starbase(starbase)

    def store_starbase(self, starbase):
        """
        Store a stabase in the object and trigger a save event
        :param starbase: Starbase object to save
        :return:
        """
        self.starbases[starbase.id] = starbase
        self.trigger_save()

    def delete_starbase(self, starbaseid):
        del self.starbases[starbaseid]
        self.trigger_save()

    def get_all_starbases(self):
        return self.starbases.values()

    def get_starbase_by_id(self, id: int):
        try:
            return self.starbases[id]
        except KeyError:
            return None

    def add_poco(self, poco):
        self.store_poco(poco)

    def store_poco(self, poco):
        self.pocos[poco.id] = poco
        self.trigger_save()

    def get_all_pocos(self):
        return self.pocos.values()

    def get_pos_contents(self, corp_id, starbase):
        contents_json = self._get_seat_pos_contents(corp_id, starbase.id)
        modules = []
        for module in contents_json['modules']:
            # TODO: use a factory and abstract types
            module = Module(module['detail'])
