# Project description

The Bill Calculator tool intends to provide a generic tool for manipulating the tariffs of electricity, with a emphasis on US tariffs. A tariff is composed of various type of charges and credits, that fall into one of the following rate type:

 - *FIXED*: a fixed charge, generally expressed in $/day or $/month.
 - *ENERGY*: a charge per energy consumption, generally expressed in $/kWh. This charge may vary during the day, and may be different for each month.
 - *DEMAND*: a charge per demand, generally expressed in $/kW. The demand is defined as the maximum of the power consumption average over 15 minutes, taken over the whole billing period. The demand may also be applied to specific hours of the day.

The tool aims to wrap up the complexity of the bill calculation, that can include Time Of Use energy, flat demand, Time Of Use demand, Peak Pricing Day charges, non-Peak Pricing Day credits, etc.

The folder 'cost_calculator' contains the source code of the Bill Calculator. The rest of the README describes how to instanciate the main classes and their useful methods.

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

# Configuring

Set PYTHONPATH to the root directory before running:
$> export PYTHONPATH=$PYTHONPATH:/path/to/electricity-cost-calculator

# From OpenEI tariff to the Bill Calculator

## Run the test file

`python openei_test.py`

This must output the electricity bill for jan 1 2017 -> march 31 2017

## TODO list:

- The bill for demand charge: add Seasonal demand to TOU demand
- The bill for energy charge: enable residential tiers
- OpenEI tariff extraction: create a "tariff structure" (eia ID, Res/Comm/Ind, Trans/Prim/Sec, TOU or not, Option, etc)
- OpenEI tariff extraction: from the "tariff structure", create the appropriate "TariffBase" children structures
