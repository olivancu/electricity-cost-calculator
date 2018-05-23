__author__ = 'Olivier Van Cutsem'

from cost_calculator.tariff_structure import *
from cost_calculator.rate_structure import *

import time
from datetime import datetime
import requests

# ----------- FUNCTIONS SPECIFIC TO OpenEI REQUESTS -------------- #


class OpenEI_tariff(object):

    URL_OPENEI = 'https://api.openei.org/utility_rates'
    API_KEY = 'BgEcyD9nM0C24J2vL4ezN7ZNAllII0vKA9l7UEBu'
    FORMAT = 'json'
    VERSION = 'latest'
    DIRECTION_SORT = 'asc'
    DETAIL = 'full'
    LIMIT = '500'
    ORDER_BY_SORT = 'startdate'

    def __init__(self, utility_id, sector, tariff_rate_of_interest, distrib_level_of_interest='Secondary', tou=False):

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
        self.tou = tou

        # The raw filtered answer from an API call
        self.data_openei = None

    def call_api(self):

        r = requests.get(self.URL_OPENEI, params=self.req_param)
        data_openei = r.json()

        # TODO: this is only valid for the A-10 ! One needs to be more robust and look at the other fields of the answer

        data_filtered = data_openei['items']
        data_filtered = [v for v in data_filtered if self.tariff_rate_of_interest in v['name']]
        data_filtered = [v for v in data_filtered if self.distrib_level_of_interest in v['name']]
        if self.tou:
            data_filtered = [v for v in data_filtered if 'TOU' in v['name']]
        # print_json(data_filtered)  # TEST PURPOSE

        # Make sure we work with integer timestamps
        for rate_data in data_filtered:
            # Starting time
            if not (type(rate_data['startdate']) is int):
                t_s = time.mktime(
                    datetime.strptime(rate_data['startdate'], '%Y-%m-%dT%H:%M:%S.000Z').timetuple())  # Always specified
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

        print "{0} blocks of TOU data, ready to be used !".format(len(data_filtered))

        # Store internally the filtered result
        self.data_openei = data_filtered


def tariff_struct_from_openei_data(openei_tarif_obj, bill_calculator):
    """
    From a set of blocks coming from the OpenEI API, merge the block and extract the useful info
    :return: a formatted structure as explained above
    """

    tariff_struct = {}

    for block_rate in openei_tarif_obj.data_openei:

        # Tariff starting and ending dates
        tariff_dates = (datetime.fromtimestamp(block_rate['startdate']), datetime.fromtimestamp(block_rate['enddate']))

        # --- Fix charges
        tariff_fix = block_rate['fixedchargefirstmeter']

        period_fix_charge = TariffElemPeriod.MONTHLY

        if '/day' in block_rate['fixedchargeunits']:
            period_fix_charge = TariffElemPeriod.DAILY

        bill_calculator.add_tariff(FixedTariff(tariff_dates, tariff_fix, period_fix_charge), str(TariffType.FIX_CUSTOM_CHARGE.value[0]))

        # --- Demand charges
        tariff_demand_obj = get_rate_obj_from_openei(block_rate, ChargeType.DEMAND)

        bill_calculator.add_tariff(TouDemandChargeTariff(tariff_dates, tariff_demand_obj), str(TariffType.DEMAND_CUSTOM_CHARGE_SEASON.value[0]))

        # --- Energy charges
        tariff_energy_obj = get_rate_obj_from_openei(block_rate, ChargeType.ENERGY)

        bill_calculator.add_tariff(TouEnergyChargeTariff(tariff_dates, tariff_energy_obj), str(TariffType.ENERGY_CUSTOM_CHARGE.value[0]))

    return tariff_struct


def get_rate_obj_from_openei(open_ei_block, select_rate):
    """
    Analyse the block get from the OpenEI api request and transform it into a generic structure

    :param open_ei_struct: a block get from the OpenEI API
    :param select_rate: a ChargeType Enum, representing the desired rate to select
    :return: the corresponding RateSchedule object
    """

    # TODO:  !!! hardcoded for A-10 - make it generic !!!

    # TODO: use BlockRate instead of assuming it's a float !

    map_month_label = {1: 'winter', 0: 'summer'}

    rate_struct = {}

    if select_rate == ChargeType.DEMAND:
        dem_rate_list = open_ei_block['flatdemandstructure']
        dem_time_schedule_month = open_ei_block['flatdemandmonths']

        for rate_idx in range(len(dem_rate_list)):
            months_list = [i+1 for i, j in enumerate(dem_time_schedule_month) if j == rate_idx]
            rate_struct[map_month_label[rate_idx]] = {TouRateSchedule.MONTHLIST_KEY: months_list,
                                                      TouRateSchedule.DAILY_RATE_KEY: {
                                                          'allweek': {
                                                              TouRateSchedule.DAYSLIST_KEY: range(7),
                                                              TouRateSchedule.RATES_KEY: dem_rate_list[rate_idx][0]['rate']
                                                          }
                                                        }
                                                      }

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

    return TouRateSchedule(rate_struct)

