__author__ = 'Olivier Van Cutsem'

from rate_structure import *
from dateutil.relativedelta import relativedelta


class CostCalculator(object):
    """
    This class is used to manipulate the building electricity cost:
        - Bill calculation given a Smart Meter power timeseries
        - Electricity price timeseries between two dates
        - Cost coefficients over a given period, for a linear optimization problem
        - Metrics related to the tariff maximum demand

    The main component of this class is called the "tariff_structure".
    It is a dictionnary that lists electricity cost information for each type (fix, energy or demand).
    The list for each type of billing stores "blocks" of data, that collect data about the tariffication of the electricity for a specific PERIOD of time.
    Any time a new tariffication (e.g. a PDP event, or a new base tariff) must be added for a new time period, one just need to add the "block" of data in the corresponding list.

    """

    DEFAULT_TARIFF_TYPE_LIST = [ChargeType.FIXED, ChargeType.DEMAND, ChargeType.ENERGY]

    def __init__(self, type_tariffs_list=None):
        """
        Initialize the class instance

        :param type_tariffs_list: [optional] the main type of tariffs used to describe the whole billing logic.
        DEFAULT_TARIFF_TYPE_LIST is used if type_tariffs_list is not specified.

        Note: the method 'add_tariff' is used to build the core "tariff_structure" object structure.
        """

        # This is the main structure, listing all the "tariff blocks" making up the whole tariff logic
        self.__tariffstructures = {}

        if type_tariffs_list is None:  # The 3 "basic" tariff types as the default ones
            type_tariffs_list = self.DEFAULT_TARIFF_TYPE_LIST

        # Initialize the list of "tariff blocks"
        for t in type_tariffs_list:
            self.__tariffstructures[t] = []

    # --- Useful methods

    def compute_bill(self, df):
        """
        Return the bill corresponding to the energy data in a data frame:

        {
            "YYYY-MM":
            {
                "fix": (int, float),        -> the #days and the corresponding cost in the month
                "demand": (float, float),   -> the max power (kW) and the corresponding cost ($) in the month
                "energy": (float, float)    -> the tot energy (kWh) and the corresponding cost ($) in the month
            },
            ...
        }

        :param df: a pandas dataframe containing power consumption
        :return: a dictionary representing the bill as described above
        --> TODO: should it return a pandas dataframe instead ?
        """

        ret = {}

        # Initialize the return structure
        t_s = df.index[0]
        t_i = datetime(t_s.year, t_s.month, 1)
        while t_i <= df.index[-1]:
            ret[t_i.strftime("%Y-%m")] = {str(ChargeType.FIXED): (0, 0), str(ChargeType.ENERGY): (0, 0), str(ChargeType.DEMAND): (0, 0)}
            t_i += relativedelta(months=+1)

        # Fixed cost in the period
        l_fix_blocks = self.get_tariff_struct(ChargeType.FIXED, (df.index[0], df.index[-1]))
        for fix_block in l_fix_blocks:
            fix_cost_list = fix_block.compute_bill(df)  # return a dict of time-period pointing to tuple
            for time_label, fix_data in fix_cost_list.items():
                ret[time_label][str(ChargeType.FIXED)] = (ret[time_label][str(ChargeType.FIXED)][0] + fix_data[0],
                                                          ret[time_label][str(ChargeType.FIXED)][1] + fix_data[1])

        # Energy cost in the period
        l_energy_blocks = self.get_tariff_struct(ChargeType.ENERGY, (df.index[0], df.index[-1]))
        for energy_block in l_energy_blocks:
            energy_cost_list = energy_block.compute_bill(df)  # returns a dict of time-period pointing to tuple
            for time_label, energy_data in energy_cost_list.items():
                ret[time_label][str(ChargeType.ENERGY)] = (ret[time_label][str(ChargeType.ENERGY)][0] + energy_data[0],
                                                           ret[time_label][str(ChargeType.ENERGY)][1] + energy_data[1])

        # Demand cost in the period
        l_demand_blocks = self.get_tariff_struct(ChargeType.DEMAND, (df.index[0], df.index[-1]))
        for demand_block in l_demand_blocks:
            demand_cost_list = demand_block.compute_bill(df)  # return a list of
            for time_label, demand_data in demand_cost_list.items():
                if demand_data[0] > ret[time_label][str(ChargeType.DEMAND)][0]:  # this power demand is greater than the one observed previously in this month
                    ret[time_label][str(ChargeType.DEMAND)] = (ret[time_label][str(ChargeType.DEMAND)][0] + demand_data[0],
                                                               ret[time_label][str(ChargeType.DEMAND)][1] + demand_data[1])

        return ret

    def get_electricity_price(self, range_date, timestep):
        """
        Compute the price of electricity for the specified time frame 'range_date', sample at 'timestep' period.

        :param range_date: a tuple (t_start, t_end) of type 'datetime', representing timestamps
        :param timestep: an element of TariffElemPeriod (1h, 30min or 15min), representing the sampling period
        :return: ?
        ---> TODO: what electricity price? energy, demand, fix ?
        """

        pass

    def get_linopt_coefficients(self, range_date, timestep):
        """
        ---> TODO: TBD more precisely ?

        This function formats the coefficients of the linear optimization problem formulation, in the time frame
        specified in 'range_date' and at the period specified by 'timestep'.

        More specifically:
         - A timeseries where, for each period, the coefficient of the energy price for this period, sampled at
         timestep 'timestep'.
         - A coefficient for the power demand over the period

        :param range_date: a tuple (t_start, t_end) of type 'datetime', storing the timestamp
        :param timestep: an element of TariffElemPeriod (1h, 30min or 15min), representing the sampling period

        :return: a dictionnary formatted as following:
        {
            "energy_coefficients": pandas dataframe that contains the corresponding energy coefficient,
            "power_coefficients": float that represents the demand coefficient
        }
        """

        pass

    # --- Construction methods

    def add_tariff(self, tariff_obj, type_rate):
        """
        Add a tariff block structure that fell into the category "type_rate"
        :param tariff_obj: a TariffBase (or children) object
        :param type_rate: the type of tariff, in the keys given to the constructor
        :return: /
        """

        self.__tariffstructures[type_rate].append(tariff_obj)

    def get_tariff_struct(self, type_rate, dates=None):
        """
        Get the list of "tariff blocks" that influence the bill for the type of tariff "type_rate".
        If "dates" is specified, only the blocks that are effective for that period are returned
        :param type_rate: a sub-class of TariffBase
        :param dates:[optional] a tuple of type datetime defining the period of selection
        :return: a list of TariffBase (or children) describing the tariffs
        """

        list_struct = self.__tariffstructures[type_rate]

        if dates is None:
            return list_struct
        else:
            (start_sel, end_sel) = dates

            return [obj for obj in list_struct if ((obj.startdate <= start_sel <= obj.enddate) or (start_sel <= obj.startdate <= end_sel))]
