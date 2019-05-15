__author__ = 'Olivier Van Cutsem'

from electricitycostcalculator.cost_calculator.cost_calculator import CostCalculator
from electricitycostcalculator.openei_tariff.openei_tariff_analyzer import *
import pandas as pd

# ----------- TEST DEMO -------------- #
READ_FROM_JSON = True

# useful functions
def utc_to_local(data, local_zone="America/Los_Angeles"):
    '''
    This method takes in pandas DataFrame and adjusts index according to timezone in which is requested by user
    '''

    data = data.tz_convert(local_zone)  # accounts for localtime shift
    # Gets rid of extra offset information so can compare with csv data
    data = data.tz_localize(None)

    return data

if __name__ == '__main__':

    meter_uuid = 'e9c51ce5-4aa1-399c-8172-92073e273a0b'
    tariff_openei_data = OpenEI_tariff(utility_id='14328',
                  sector='Commercial',
                  tariff_rate_of_interest='A-6',
                  distrib_level_of_interest=None,  # it is at the secondary level, so not specified in the name
                  phasewing=None,  # the word 'Poly' is to be excluded, because the names may omit this info ..
                  tou=True,
                  option_exclusion=['(X)', '(W)', 'Poly'])  # Need to reject the option X and W

    # Instantiate the bill-calculator object

    print("--- Loading meter data ...")
    df = pd.read_csv('meter.csv', index_col=0)  # import times series energy data for meters
    df.index.name = 'Time'
    df = df.set_index(pd.to_datetime(df.index, infer_datetime_format=True, utc=True))
    df["date"] = df.index

    data_meter = df[meter_uuid]
    data_meter = utc_to_local(data_meter, local_zone="America/Los_Angeles")

    print("--- Calling API or READING FROM JSON ...")

    if READ_FROM_JSON:

        if tariff_openei_data.read_from_json() == 0:
            print("Tariff read from JSON successful")
        else:
            print("An error occurred when reading the JSON file")
            exit()

        print("--- Bill calculation ...")
    else:   # This calls the API to internally store the raw data that has to be analyzed, and write as a JSON file
        tariff_openei_data.call_api(store_as_json=True)
    bill_calc = CostCalculator()
    #
    # Load the tariff information and fill the object

    tariff_struct_from_openei_data(tariff_openei_data, bill_calc)  # This analyses the raw data from the openEI request and populate the "CostCalculator" object

    # Useful information of the Tariff
    print("Tariff {0} of utility #{1} (TOU {2}, Grid level {3}, Phase-wing {4})".format(tariff_openei_data.tariff_rate_of_interest,
                                                                                        tariff_openei_data.req_param['eia'],
                                                                                        tariff_openei_data.tou,
                                                                                        tariff_openei_data.distrib_level_of_interest,
                                                                                        tariff_openei_data.phase_wing))

    print(" - Found {0} tariff blocks from OpenEI".format(len(bill_calc.get_tariff_struct(label_tariff=str(TariffType.ENERGY_CUSTOM_CHARGE.value)))))
    print(" - Valid if peak demand is between {0} kW and {1} kW".format(bill_calc.tariff_min_kw, bill_calc.tariff_max_kw))
    print(" - Valid if energy demand is between {0} kWh and {1} kWh".format(bill_calc.tariff_min_kwh, bill_calc.tariff_max_kwh))
    print(" ----------------------")

    # BILLING PERIOD
    start_date_bill = datetime(2017, 7, 1, hour=0, minute=0, second=0)
    end_date_bill = datetime(2017, 7, 30, hour=23, minute=59, second=59)
    mask = (data_meter.index >= start_date_bill) & (data_meter.index <= end_date_bill)
    data_meter = data_meter.loc[mask]
    data_meter = data_meter.fillna(0)

    # 1) Get the bill over the period
    print("Calculating the bill for the period {0} to {1}".format(start_date_bill, end_date_bill))
    bill = bill_calc.compute_bill(data_meter, monthly_detailed=True)
    t, tt, ttt = bill_calc.print_aggregated_bill(bill)
    print(t)

    # 2) Get the electricity price per type of metric, for the 7th of JAN 2017
    start_date_sig= datetime(2019, 7, 1, hour=0, minute=0, second=0)
    end_date_sig = datetime(2019, 7, 7, hour=23, minute=59, second=59)
    timestep = TariffElemPeriod.QUARTERLY  # We want a 1h period

    price_elec, map = bill_calc.get_electricity_price((start_date_sig, end_date_sig), timestep)

    print(price_elec)
