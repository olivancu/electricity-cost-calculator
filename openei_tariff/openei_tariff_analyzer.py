__author__ = 'Olivier Van Cutsem'
#bill_calculator_lib.
from cost_calculator.tariff_structure import *
from cost_calculator.rate_structure import *

import time
from datetime import datetime
import requests
import json
import pytz

# ----------- FUNCTIONS SPECIFIC TO OpenEI REQUESTS -------------- #

THIS_PATH = 'openei_tariff/'
SUFFIX_REVISED = '_revised'  # this is the suffix we added to the json filename after correctly the OpenEI data manually

class OpenEI_tariff(object):

    URL_OPENEI = 'https://api.openei.org/utility_rates'
    API_KEY = 'BgEcyD9nM0C24J2vL4ezN7ZNAllII0vKA9l7UEBu'
    FORMAT = 'json'
    VERSION = 'latest'
    DIRECTION_SORT = 'asc'
    DETAIL = 'full'
    LIMIT = '500'
    ORDER_BY_SORT = 'startdate'

    def __init__(self, utility_id, sector, tariff_rate_of_interest, distrib_level_of_interest='Secondary', phasewing='Single', tou=False, option_mandatory=None, option_exclusion=None):

        self.req_param = {}

        # Request param
        self.req_param['api_key'] = self.API_KEY
        self.req_param['eia'] = utility_id
        self.req_param['sector'] = sector

        self.req_param['format'] = self.FORMAT
        self.req_param['version'] = self.VERSION

        self.req_param['direction'] = self.DIRECTION_SORT
        self.req_param['detail'] = self.DETAIL
        self.req_param['limit'] = self.LIMIT
        self.req_param['orderby'] = self.ORDER_BY_SORT

        # Post-req filter
        self.tariff_rate_of_interest = tariff_rate_of_interest
        self.distrib_level_of_interest = distrib_level_of_interest
        self.phase_wing = phasewing
        self.tou = tou
        self.option_exclusion = option_exclusion
        self.option_mandatory = option_mandatory

        # The raw filtered answer from an API call
        self.data_openei = None

    def call_api(self, store_as_json=None):

        r = requests.get(self.URL_OPENEI, params=self.req_param)
        data_openei = r.json()
        data_filtered = []

        for data_block in data_openei['items']:
            print data_block['name']
            # Check the tariff name, this is stored in the field "name"
            if self.tariff_rate_of_interest not in data_block['name'] and self.tariff_rate_of_interest + '-' not in data_block['name']:
                continue
            print(" - {0}".format(data_block['name']))

            # Check the wiring option
            if self.phase_wing is not None:
                if 'phasewiring' in data_block.keys():
                    if not(self.phase_wing in data_block['phasewiring']):
                        continue
                else:  # check the title if this field is missing
                    if self.phase_wing not in data_block['name']:  # TODO: be sure that Single / Poly is always written in the name
                        continue

            # Check the grid level option
            if self.distrib_level_of_interest is not None:
                if self.distrib_level_of_interest not in data_block['name']:
                    continue

            print(" -- {0}".format(data_block['name']))
            # Check the Time of Use option
            if (self.tou and 'TOU' not in data_block['name']) or (not self.tou and 'TOU' in data_block['name']):
                continue

            # Ensure some options on the rate:
            if self.option_mandatory is not None:
                continue_block = False
                for o in self.option_mandatory:
                    if o not in data_block['name']:
                        continue_block = True
                        break
                if continue_block:
                    continue

            # Exclude some options on the rate
            if self.option_exclusion is not None:
                continue_block = False
                for o in self.option_exclusion:
                    if o in data_block['name']:
                        continue_block = True
                        break
                if continue_block:
                    continue

            #print(" -------> {0}".format(data_block['name']))
            # The conditions are fulfilled: add this block
            data_filtered.append(data_block)

        # Make sure we work with integer timestamps
        for rate_data in data_filtered:
            # Starting time
            if not (type(rate_data['startdate']) is int):
                t_s = time.mktime(
                    datetime.strptime(rate_data['startdate'],
                                      '%Y-%m-%dT%H:%M:%S.000Z').timetuple())  # Always specified
                rate_data['startdate'] = t_s

            # Ending time
            if 'enddate' in rate_data.keys():
                if not (type(rate_data['enddate']) is int):
                    t_e = time.mktime(datetime.strptime(rate_data['enddate'],
                                                        '%Y-%m-%dT%H:%M:%S.000Z').timetuple())  # maybe not specified - assumed it's until now
                    rate_data['enddate'] = t_e
            else:
                rate_data['enddate'] = time.time()

        # Make sure that the dates are consecutive
        for i in range(len(data_filtered) - 1):
            data_cur = data_filtered[i]
            data_next = data_filtered[i + 1]
            # Replace END time of the current elem by the START time of the next one if necessary
            data_cur['enddate'] = min(data_next['startdate'], data_cur['enddate'])

        # Re-encode the date as human
        for block in data_filtered:
            block['startdate'] = datetime.fromtimestamp(block['startdate'], tz=pytz.timezone("UTC")).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            block['enddate'] = datetime.fromtimestamp(block['enddate'], tz=pytz.timezone("UTC")).strftime('%Y-%m-%dT%H:%M:%S.000Z')

        # Store internally the filtered result
        self.data_openei = data_filtered

        # Store the result of this processed API request in a JSON file that has the name built from the tariff info
        if store_as_json is not None:
            filename = self.json_filename
            with open(THIS_PATH+filename+'.json', 'w') as outfile:
                json.dump(data_filtered, outfile, indent=2, sort_keys=True)

    def read_from_json(self):
        """
        Read tariff data from a JSON file to build the internal structure. The JSON file
        :return:
         - 0 if the data has been loaded from the json successfully,
         - 1 if the data couldn't be laod from the json file
         - 2 if the file couldn't be read
        """
        print THIS_PATH+self.json_filename
        try:
            with open(THIS_PATH+self.json_filename+SUFFIX_REVISED+'.json', 'r') as input_file:
                try:
                    self.data_openei = json.load(input_file)
                except ValueError:
                    print 'cant parse json'
                    return 1
        except EnvironmentError:
            print 'cant open file'
            return 2  # everything went well

        # Encode the start/end dates as integers
        for block in self.data_openei:
            block['enddate'] = datetime.strptime(block['enddate'], '%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=pytz.timezone('UTC'))
            block['startdate'] = datetime.strptime(block['startdate'], '%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=pytz.timezone('UTC'))

        print self.data_openei

        return 0

    @property
    def json_filename(self):

        # Conditional field: TOU or nothing
        if_tou = ''
        if self.tou:
            if_tou = '_TOU'

        # Wiring
        phase_info = ''
        if self.phase_wing is not None:
            phase_info = '_phase'+self.phase_wing

        # Grid level
        gridlevel_info = ''
        if self.distrib_level_of_interest is not None:
            gridlevel_info = '_gridlevel'+self.distrib_level_of_interest

        return 'u'+self.req_param['eia']+'_'+self.req_param['sector']+'_'+self.tariff_rate_of_interest+if_tou+phase_info+gridlevel_info


def tariff_struct_from_openei_data(openei_tarif_obj, bill_calculator):
    """
    Analyze the content of an OpenEI request in order to fill a CostCalculator object
    :param openei_tarif_obj: an instance of OpenEI_tariff that already call the API
    :param bill_calculator: an (empty) instance of CostCalculator
    :return: /
    """

    tariff_struct = {}

    for block_rate in openei_tarif_obj.data_openei:

        # Tariff starting and ending dates
        tariff_dates = (block_rate['startdate'], block_rate['enddate'])

        # --- Fix charges
        tariff_fix = block_rate['fixedchargefirstmeter']

        period_fix_charge = TariffElemPeriod.MONTHLY

        if '/day' in block_rate['fixedchargeunits']:
            period_fix_charge = TariffElemPeriod.DAILY

        bill_calculator.add_tariff(FixedTariff(tariff_dates, tariff_fix, period_fix_charge), str(TariffType.FIX_CUSTOM_CHARGE.value[0]))

        # --- Demand charges
        tariff_demand_obj = get_rate_obj_from_openei(block_rate, ChargeType.DEMAND)

        if tariff_demand_obj is not None:
            bill_calculator.add_tariff(TouDemandChargeTariff(tariff_dates, tariff_demand_obj), str(TariffType.DEMAND_CUSTOM_CHARGE_SEASON.value[0]))

        # --- Energy charges
        tariff_energy_obj = get_rate_obj_from_openei(block_rate, ChargeType.ENERGY)

        if tariff_energy_obj is not None:
            bill_calculator.add_tariff(TouEnergyChargeTariff(tariff_dates, tariff_energy_obj), str(TariffType.ENERGY_CUSTOM_CHARGE.value[0]))

    # Other useful information, beside the tariff
    # Loop over all the blocks to be sure, maybe such fields are missing in some ..
    for block_rate in openei_tarif_obj.data_openei:
        if 'peakkwcapacitymax' in block_rate.keys():
            bill_calculator.tariff_max_kw = block_rate['peakkwcapacitymax']
        if 'peakkwcapacitymin' in block_rate.keys():
            bill_calculator.tariff_min_kw = block_rate['peakkwcapacitymin']

        if 'peakkwhusagemax' in block_rate.keys():
            bill_calculator.tariff_max_kwh = block_rate['peakkwhusagemax']
        if 'peakkwhusagemin' in block_rate.keys():
            bill_calculator.tariff_min_kwh = block_rate['peakkwhusagemin']

def get_rate_obj_from_openei(open_ei_block, select_rate):
    """
    Analyse the block get from the OpenEI api request and transform it into a generic structure

    :param open_ei_struct: a block get from the OpenEI API
    :param select_rate: a ChargeType Enum, representing the desired rate to select
    :return: the corresponding RateSchedule object
    """

    # TODO:  !!! hardcoded for A-10 - make it generic !!!

    # TODO later: use BlockRate instead of assuming it's a float !

    map_month_label = {1: 'winter', 0: 'summer'}

    rate_struct = {}

    if select_rate == ChargeType.DEMAND:

        if 'flatdemandstructure' in open_ei_block.keys(): # there is a flat demand rate
            dem_rate_list = open_ei_block['flatdemandstructure']
            dem_time_schedule_month = open_ei_block['flatdemandmonths']

            for rate_idx in range(len(dem_rate_list)):
                months_list = [i+1 for i, j in enumerate(dem_time_schedule_month) if j == rate_idx]
                rate_struct[map_month_label[rate_idx]] = {TouRateSchedule.MONTHLIST_KEY: months_list,
                                                          TouRateSchedule.DAILY_RATE_KEY: {
                                                              'allweek': {
                                                                  TouRateSchedule.DAYSLIST_KEY: range(7),
                                                                  TouRateSchedule.RATES_KEY: 24 * [dem_rate_list[rate_idx][0]['rate']]
                                                              }
                                                            }
                                                          }

        if 'demandratestructure' in open_ei_block.keys():  # there is a TOU demand rate
            pass  # todo for E19 and SCE !

    elif select_rate == ChargeType.ENERGY:
        en_rate_list = open_ei_block['energyratestructure']

        weekdays_schedule = open_ei_block['energyweekdayschedule']
        weekends_schedule = open_ei_block['energyweekendschedule']

        for m_i in range(12):

            already_added = False
            daily_weekdays_rate = map(lambda(x): en_rate_list[x][0]['rate'], weekdays_schedule[m_i])
            daily_weekends_rate = map(lambda (x): en_rate_list[x][0]['rate'], weekends_schedule[m_i])

            # Check if this schedule is already present
            for m_group_lab, m_group_data in rate_struct.items():
                if daily_weekdays_rate == m_group_data[TouRateSchedule.DAILY_RATE_KEY]['weekdays'][TouRateSchedule.RATES_KEY] and daily_weekends_rate == m_group_data[TouRateSchedule.DAILY_RATE_KEY]['weekends'][TouRateSchedule.RATES_KEY] :
                    m_group_data[TouRateSchedule.MONTHLIST_KEY].append(m_i+1)
                    already_added = True
                    break

            if not already_added:
                rate_struct['m_'+str(m_i+1)] = {TouRateSchedule.MONTHLIST_KEY: [m_i+1],
                                                TouRateSchedule.DAILY_RATE_KEY: {
                                                    'weekdays': {
                                                       TouRateSchedule.DAYSLIST_KEY: [1, 2, 3, 4, 5],
                                                       TouRateSchedule.RATES_KEY: daily_weekdays_rate
                                                    },
                                                    'weekends': {
                                                       TouRateSchedule.DAYSLIST_KEY: [6, 0],
                                                       TouRateSchedule.RATES_KEY: daily_weekends_rate}
                                                }
                                                }
    if rate_struct != {}:
        return TouRateSchedule(rate_struct)
    else:
        return None
