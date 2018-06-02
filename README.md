# Project description

The Bill Calculator tool intends to provide a generic tool - at least for US - for manipulating the tariffs of electricity. A tariff is composed of various type of charges and credits, that fall into one of the following rate type:

 - FIXED: a fixed charge, generally expressed in $/day or $/month
 - ENERGY: a charge per energy consumption, generally expressed in $/kWh. This charge may vary during the day, and be different for each month
 - DEMAND: a charge per demand, generally expressed in $/kW. The demand is defined as the maximum of the power consumption average over 15 minutes, taken over the whole billing period.

The tool aims to wrap up the complexity of the bill calculation, that can include together Time Of Use energy, flat demand, Time Of Use demand, Peak Pricing Day charges, non-Peak Pricing Day credits, etc.

The folder 'cost_calculator' contains the source code of the Bill Calculator 

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

TODO

# Bill Calculator methods

## Compute the billl

TODO

## Get the prices signal over a period

TODO

# OpenEI test file

`python openei_test.py`

This outputs the bill linked to an energy meter of a building, given a specific tariff. 

TODO: 
