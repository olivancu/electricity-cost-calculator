__author__ = 'Olivier Van Cutsem'

from cost_calculator.cost_calculator import CostCalculator
import json
import pandas as pd
from openei_tariff.openei_tariff_analyzer import *
import matplotlib.pyplot as plt
import pytz

# ----------- TEST DEMO -------------- #

# UTILITY ID: {PG&E: 14328, SCE: 17609}

# TODO: read this from a CSV ...
map_site_to_tariff = {
    '4c95836f-6bdb-3adc-ac5e-4c787ae027c7':  # Orinda Library
    OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='A-10',
                  distrib_level_of_interest='Secondary',
                  phasewing=None,
                  tou=True),
    '4d95d5ce-de62-3449-bd58-4dcad75b526d':  # Recreational center
    OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='A-1 Small General Service',  # need to add Small General Service to get the right data ..
                  distrib_level_of_interest=None,
                  phasewing='Single',
                  tou=True),
    'e9c51ce5-4aa1-399c-8172-92073e273a0b':  # Fire station 8, Hayward
    OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='A-6',
                  distrib_level_of_interest=None,  # it is at the secondary level, so not specified in the name
                  phasewing=None,  # the word 'Poly' is to be excluded, because the names may omit this info ..
                  tou=True,
                  option_exclusion=['(X)', '(W)', 'Poly']),  # Need to reject the option X and W
    '68e04192-e924-36b8-9c5e-f072bd93ed07':  # Avenal movie theater
    OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='E-19',
                  distrib_level_of_interest='Secondary',
                  phasewing=None,
                  tou=True,
                  option_exclusion=['Option R', 'Voluntary']),
}

# useful functions
def print_json(json_dict):
    print json.dumps(json_dict, indent=2, sort_keys=True)

if __name__ == '__main__':

    # Instantiate the bill-calculator object

    print("--- Loading meter data ...")

    meter_uuid = '4d95d5ce-de62-3449-bd58-4dcad75b526d'
    print("Data from GreenButton meter uuid '{0}'".format(meter_uuid))

    df = pd.read_csv('meter.csv', index_col=0)  # import times series energy data for meters
    df.index.name = 'Time'
    df.index = df.index.map(pd.to_datetime)

    df["date"] = df.index.date
    df["time"] = df.index.hour

    data_meter = df[meter_uuid]

    # Specify the Utility tariff we're going to analyze

    print("--- Calling API ...")
    tariff_openei_data = map_site_to_tariff[meter_uuid]  # This points to an object

    tariff_openei_data.call_api(store_as_json=True)  # WARNING: this will erase the JSON with OpenEI data !

    if tariff_openei_data.read_from_json() == 0:  # This calls the API to internally store the raw data that has to be analyzed, and write as a JSON file
        print "Tariff read from JSON successful"
    else:
        print "An error occurred when reading the JSON file"
        exit()

    print("--- Bill calculation ...")
    bill_calc = CostCalculator()

    # Load the tariff information and fill the object

    tariff_struct_from_openei_data(tariff_openei_data, bill_calc)  # This analyses the raw data from the openEI request and populate the "CostCalculator" object

    # Useful information of the Tariff
    print("Tariff {0} of utility #{1} (TOU {2}, Grid level {3}, Phase-wing {4})".format(tariff_openei_data.tariff_rate_of_interest,
                                                                                        tariff_openei_data.req_param['eia'],
                                                                                        tariff_openei_data.tou,
                                                                                        tariff_openei_data.distrib_level_of_interest,
                                                                                        tariff_openei_data.phase_wing))

    print(" - Found {0} tariff blocks from OpenEI".format(len(bill_calc.get_tariff_struct(label_tariff=str(TariffType.ENERGY_CUSTOM_CHARGE.value[0])))))
    print(" - Valid if peak demand is between {0} kW and {1} kW".format(bill_calc.tariff_min_kw, bill_calc.tariff_max_kw))
    print(" - Valid if energy demand is between {0} kWh and {1} kWh".format(bill_calc.tariff_min_kwh, bill_calc.tariff_max_kwh))
    print(" ----------------------")

    # BILLING PERIOD
    start_date_bill = datetime(2017, 7, 23, hour=0, minute=0, second=0, tzinfo=pytz.timezone("US/Pacific"))
    end_date_bill = datetime(2017, 8, 21, hour=23, minute=59, second=59, tzinfo=pytz.timezone("US/Pacific"))

    mask = (data_meter.index >= start_date_bill) & (data_meter.index <= end_date_bill)
    data_meter = data_meter.loc[mask]

    # 1) Get the bill over the period
    print("Calculating the bill for the period {0} to {1}".format(start_date_bill, end_date_bill))
    bill = bill_calc.compute_bill(data_meter)
    print(bill)
    t, tt, ttt = bill_calc.print_aggregated_bill(bill)

    # 2) Get the electricity price per type of metric, for the 7th of JAN 2017


    timestep = TariffElemPeriod.HOURLY  # We want a 1h period

    price_elec, map = bill_calc.get_electricity_price((start_date_bill, end_date_bill), timestep)

    print list(price_elec.loc[:, 'customer_energy_charge'])
