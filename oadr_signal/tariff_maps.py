from openei_tariff.openei_tariff_analyzer import *
tariff_maps= {
            'PGEA10': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-10', distrib_level_of_interest='Secondary', phasewing=None, tou=True),

            'PGEA01': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-1 Small General Service', distrib_level_of_interest=None, phasewing='Single', tou=True),

            'PGEA06': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-6', distrib_level_of_interest=None, phasewing=None, tou=True, option_exclusion=['(X)', '(W)', 'Poly']),

            'PGEE19': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='E-19', distrib_level_of_interest='Secondary', phasewing=None, tou=True, option_exclusion=['Option R', 'Voluntary']),

            # 'TOU-8B': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-10',
            #              distrib_level_of_interest='Secondary', phasewing=None, tou=True),
            # 'TGS3': OpenEI_tariff(utility_id='14328', sector='Commercial', tariff_rate_of_interest='A-10',
            #              distrib_level_of_interest='Secondary', phasewing=None, tou=True)
     }