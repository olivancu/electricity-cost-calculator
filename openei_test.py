__author__ = 'Olivier Van Cutsem'

from cost_calculator.cost_calculator import CostCalculator
import json
import pandas as pd
from openei_tariff.openei_tariff_analyzer import *

# ----------- TEST DEMO -------------- #

# UTILITY ID: {PG&E: 14328, SCE: 17609}

# TODO: read this from a CSV ...
map_site_to_tariff = {
    '4c95836f-6bdb-3adc-ac5e-4c787ae027c7':  # Orinda Library
    OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='A-10',
                  distrib_level_of_interest='Secondary',
                  phasewing='Single Phase',
                  tou=False)
}

# useful functions
def print_json(json_dict):
    print json.dumps(json_dict, indent=2, sort_keys=True)

if __name__ == '__main__':

    # Instantiate the bill-calculator object

    print("--- Loading meter data ...")

    meter_uuid = '4c95836f-6bdb-3adc-ac5e-4c787ae027c7'
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

    tariff_openei_data.call_api()  # This calls the API to internally store the raw data that has to be analyzed

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
    start_date_bill = datetime(2017, 7, 23, hour=0, minute=0, second=0)
    end_date_bill = datetime(2017, 8, 22, hour=23, minute=59, second=59)

    mask = (data_meter.index >= start_date_bill) & (data_meter.index <= end_date_bill)
    data_meter = data_meter.loc[mask]

    # 1) Get the bill over the period
    print("Calculating the bill for the period {0} to {1}".format(start_date_bill, end_date_bill))
    bill = bill_calc.compute_bill(data_meter)
    print_json(bill)
    bill_calc.print_bill(bill)

    # 2) Get the electricity price per type of metric, for the 7th of JAN 2017

    start_date_price = datetime(2017, 1, 7, hour=0, minute=0, second=0)
    end_date_price = datetime(2017, 1, 7, hour=23, minute=59, second=59)

    timestep = TariffElemPeriod.HOURLY  # We want a 1h period

    #print bill_calc.get_electricity_price((start_date_price, end_date_price), timestep)
