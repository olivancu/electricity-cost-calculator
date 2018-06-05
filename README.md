# Project description

The Bill Calculator tool intends to provide a generic tool - at least for US - for manipulating the tariffs of electricity. A tariff is composed of various type of charges and credits, that fall into one of the following rate type:

 - FIXED: a fixed charge, generally expressed in $/day or $/month
 - ENERGY: a charge per energy consumption, generally expressed in $/kWh. This charge may vary during the day, and be different for each month
 - DEMAND: a charge per demand, generally expressed in $/kW. The demand is defined as the maximum of the power consumption average over 15 minutes, taken over the whole billing period.

The tool aims to wrap up the complexity of the bill calculation, that can include together Time Of Use energy, flat demand, Time Of Use demand, Peak Pricing Day charges, non-Peak Pricing Day credits, etc.

The folder 'cost_calculator' contains the source code of the Bill Calculator 

## Packages dependency

pandas, holidays, datetime, enum, pytz, requests

# Bill Calculator creation

In order to use the tool, one must instanciate the CostCalculator.

```python
billcalculator_obj = CostCalculator()
```

The object must then be populated with tariff data:

```python
for tariffObj in list_of_tariff_object:
  bill_calculator.add_tariff(tariffObj, typeOfTariff)
```

where:
- tariffObj is an instance of 'TariffBase' containing the corresponding pricing information for a given period. This object is described in the section "Tariff object".
- typeOfTariff is the type of tariff corresponding to this object

By adding objects TariffObj for various periods, the whole tariff is available inside the CostCalculator object.

## Tariff object

A tariff object is an instance of 'TariffBase' or one of its childen classes. The base information common for each tariff type contains:

- A starting date: the date from which the tariff is valid
- An endid date: the date until which the tariff is valid

Each tariff has then a specific rate charge structure. The most common tariff is a Time Of Use (TOU) tariff, for which the rate pattern is identical for a group of days in the year (example: weekdays-summer, weekends-winters) and such a rate may have different values for each hour in a day.

A TOU tariff is described by instanciating the TouRateSchedule class with appropriate rate structure description. The latter is a dictionnary that maps a group of months and days in the week to a specific rate signal.

### Example of TouRateSchedule object

The first step is to describe the rates imposed by this TOU tariff. The following example assumed a price that increases from 2pm to 6pm during the weekdays of summer, and is flat for the rest of the time:

```python
rate_tou=
{
        "summer":
        {
            "months_list": [5,6,7,8,9,10],
            "daily_rates":
            {
                "weekdays:
                {
                    "days_list": [0,1,2,3,4],
                    "rates": [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
                },
                "weekends:
                {
                    "days_list": [5,6],
                    "rates": 0.2
                },
            }
        },
        "winter":
        {
            "months_list": [1,2,3,4,11,12],
            "daily_rates":
            {
                "allweek:
                {
                    "days_list": [0,1,2,3,4,6,7],
                    "rates": 0.2
                }
            }
        },
    }
}
```

The TOU tariff object can then be instanciated. Let's assume this tariff is valid from 2017-01-01 to 2017-12-31.

```python
  date_start = datetime(2017, 1, 1)
  date_end = datetime(2017, 12, 31)
  tariffObj = TouRateSchedule((date_start, date_end), rate_tou)
```

## From OpenEI tariff to the Bill Calculator

This packages provides a set of functions to pull utility tariffs from the OpenEI API (https://openei.org/services/) and create the corresponding tariff objects to be added to the CostCalculator object.
The first step consists in creating an OpenEI_tariff that describes the tariff in use. Here is an example for PG&E A-10 TOU at the Secondary level:

```python
  openei_tariff_data = OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-10', distrib_level_of_interest='Secondary', tou=True),
```
The second step is to call the API:

```python
  openei_tariff_data.call_api()
```

This method processes the raw data coming from the API and select only the tariff of interest.
The last step populates the CostCalculator object based on the OpenEI data:

```python
  bill_calculator = CostCalculator()
  tariff_struct_from_openei_data(openei_tariff_data, bill_calculator)
```

### OpenEI tariff revision

The data got from the OpenEI API might not be up-to-date or contain errors. In this case, the user might save the post-processed API call to a JSON file:

```python
  openei_tariff.call_api(store_as_json=True)
```
The user can then revise the blocks of the "tariff_yyyy.json" and save it to "tariff_yyyy_revised.json". This json file can now be used, instead of the OpenEI API call:

```python
  tariff_openei_data.read_from_json()
```

# Bill Calculator methods

## Compute the bill

Given a pandas dataframe 'data_meter' that maps date indexes to power consumption (in W), the following method computes the bill linked to the encoded tariff:

```python
  bill = bill_calculator.compute_bill(data_meter)
```
The returned structure is a dictionary that maps a cost and a metric for each type of tariff. See the method signature for further details.

Optional arguments can be specified:

 - 'column_data': select a specific column in the dataframe. Leave it when the dataframe only contains one column.
 - 'monthly_detailed': False by default, assuming that the billing period spans over the whole dataframe. Set if to True to map a bill for each month in the dataframe.


## Get the prices signal over a period

The following method returns a pandas dataframe mapping the dates in 'date_range' to the price of electricity, sampled at a period 'timestep'. The dataframe columns points to each type of tariff

```python
  date_range = (startdate, endate)
  timestep = TariffElemPeriod.QUARTERLY
  bill = bill_calculator.get_electricity_price(date_range, timestep)
```

# OpenEI test file

`python openei_test.py`

This outputs the bill linked to an energy meter of a building, given a specific tariff. 
