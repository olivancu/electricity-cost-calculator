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
