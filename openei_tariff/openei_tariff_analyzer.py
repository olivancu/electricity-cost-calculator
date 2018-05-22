
from cost_calculator.tariff_structure import *
from cost_calculator.rate_structure import *
import pickle  # for test purpose
import json
from datetime import datetime

# ----------- FUNCTIONS SPECIFIC TO OpenEI REQUESTS -------------- #


def tariff_struct_from_openei_data(bill_calculator):
    """
    From a set of blocks coming from the OpenEI API, merge the block and extract the useful info
    :return: a formatted structure as explained above
    """

    tariff_struct = {}

    openei_structure = pickle.load(open('openei_tariff/tariff_pge_a10_tou.var'))

    for block_rate in openei_structure:

        # Tariff starting and ending dates
        tariff_dates = (datetime.fromtimestamp(block_rate['startdate']), datetime.fromtimestamp(block_rate['enddate']))

        # --- Fix charges
        tariff_fix = block_rate['fixedchargefirstmeter']

        period_fix_charge = TariffElemPeriod.MONTHLY

        if '/day' in block_rate['fixedchargeunits']:
            period_fix_charge = TariffElemPeriod.DAILY

        bill_calculator.add_tariff(FixedTariff(tariff_dates, tariff_fix, period_fix_charge), ChargeType.FIXED)

        # --- Demand charges
        tariff_demand_obj = get_rate_obj_from_openei(block_rate, ChargeType.DEMAND)

        bill_calculator.add_tariff(TouDemandChargeTariff(tariff_dates, tariff_demand_obj), ChargeType.DEMAND)

        # --- Energy charges
        tariff_energy_obj = get_rate_obj_from_openei(block_rate, ChargeType.ENERGY)

        bill_calculator.add_tariff(TouEnergyChargeTariff(tariff_dates, tariff_energy_obj), ChargeType.ENERGY)

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

