import os, sys
from electricitycostcalculator.openei_tariff.openei_tariff_analyzer import OpenEI_tariff

tariff_maps= {
            'PGEA10': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-10', distrib_level_of_interest='Secondary', phasewing=None, tou=True),

            'PGEA01': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-1 Small General Service', distrib_level_of_interest=None, phasewing='Single', tou=True),

            'PGEA06': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-6', distrib_level_of_interest=None, phasewing=None, tou=True, option_exclusion=['(X)', '(W)', 'Poly']),

            'PGEE19': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='E-19', distrib_level_of_interest='Secondary', phasewing=None, tou=True, option_exclusion=['Option R', 'Voluntary']),

            'PGEE20': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='E-20', distrib_level_of_interest='Primary', phasewing=None, tou=True),

            'FLAT06': OpenEI_tariff(utility_id='90', sector='Commercial', tariff_rate_of_interest='FLAT-06', phasewing=None, tou=False, distrib_level_of_interest=None),

            'SCE08B':  OpenEI_tariff(utility_id='17609', sector='Commercial', tariff_rate_of_interest='TOU-8', distrib_level_of_interest=None,  phasewing=None, tou=True, option_mandatory=['Option B', 'under 2 kV'], option_exclusion=['Option R']),

            "SCETGS3": OpenEI_tariff(utility_id='17609', sector='Commercial', tariff_rate_of_interest='TOU-GS-3', distrib_level_of_interest=None, phasewing=None, tou=True, option_mandatory=['Option CPP', '2kV - 50kV'], option_exclusion=['Option B', 'Option A'])
     }
