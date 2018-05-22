from openei_tariff.openei_tariff_analyzer import tariff_struct_from_openei_data
from cost_calculator.cost_calculator import CostCalculator
import json
import pandas as pd
from datetime import datetime

# ----------- TEST DEMO -------------- #


def print_json(json_dict):
    print json.dumps(json_dict, indent=2, sort_keys=True)


if __name__ == '__main__':

    # Instantiate the bill-calculator object

    bill_calc = CostCalculator()

    # Load the tariff information and fill the object

    tariff_struct = tariff_struct_from_openei_data(bill_calc)

    # Load the energy consumption vector

    df = pd.read_csv('meter.csv', index_col=0)  # import times series energy data for meters
    df.index.name = 'Time'
    df.index = df.index.map(pd.to_datetime)

    df["date"] = df.index.date
    df["time"] = df.index.hour

    meter_uuid = 'd3489cfa-93a5-37e7-a274-0f35cf17b782'
    data_meter = df[meter_uuid]
    #print data_meter

    # BILLING PERIOD
    start_date = datetime(2017, 1, 1, hour=0, minute=0, second=0)
    end_date = datetime(2017, 3, 31, hour=23, minute=59, second=59)

    mask = (data_meter.index >= start_date) & (data_meter.index <= end_date)

    data_meter = data_meter.loc[mask]

    # Idea: replace NaN by 0 ?

    # 1) Get the bill over the period

    print_json(bill_calc.compute_bill(data_meter))