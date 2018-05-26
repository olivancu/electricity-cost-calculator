__author__ = 'Olivier Van Cutsem'

from rate_structure import *
from tariff_structure import TariffType, TariffElemPeriod
from dateutil.relativedelta import relativedelta
import time
import pandas as pd
import calendar


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

    # This default structure lists the tariffs type for most of the utilities in US
    DEFAULT_TARIFF_MAP = {str(TariffType.FIX_CUSTOM_CHARGE.value[0]): ChargeType.FIXED,
                          str(TariffType.ENERGY_CUSTOM_CHARGE.value[0]): ChargeType.ENERGY,
                          str(TariffType.DEMAND_CUSTOM_CHARGE_SEASON.value[0]): ChargeType.DEMAND,
                          str(TariffType.DEMAND_CUSTOM_CHARGE_TOU.value[0]): ChargeType.DEMAND,
                          str(TariffType.FIX_DREVENT_CHARGE.value[0]): ChargeType.FIXED,
                          str(TariffType.ENERGY_DREVENT_CHARGE.value[0]): ChargeType.ENERGY,
                          str(TariffType.DEMAND_DREVENT_CHARGE.value[0]): ChargeType.DEMAND,
                          }

    def __init__(self, type_tariffs_map=None):
        """
        Initialize the class instance

        :param type_tariffs_list: [optional] a dictionary that map the main type of tariffs used to describe the whole
        billing logic to their type. DEFAULT_TARIFF_TYPE_LIST is used if type_tariffs_list is not specified.

        Note: the method 'add_tariff' is used to build the core "tariff_structure" object structure.
        """

        # This is the main structure, listing all the "tariff blocks" making up the whole tariff logic
        self.__tariffstructures = {}

        if type_tariffs_map is None:  # The "basic" tariff types as the default ones
            self.type_tariffs_map = self.DEFAULT_TARIFF_MAP
        else:
            self.type_tariffs_map = type_tariffs_map

        # Initialize the list of "tariff blocks"
        for label, type_tariff in self.type_tariffs_map.items():
            self.__tariffstructures[label] = self.generate_type_tariff(type_tariff)

        # Useful data about the tariff
        self.tariff_min_kw = 0  # The minimum peak demand to stay in this tariff
        self.tariff_max_kw = float('inf')  # The maximum peak demand to stay in this tariff

        self.tariff_min_kwh = 0  # The minimum energy demand to stay in this tariff
        self.tariff_max_kwh = float('inf')  # The maximum energy demand to stay in this tariff

    # --- Useful methods

    def compute_bill(self, df, monthly_detailed=False):
        """
        Return the bill corresponding to the electricity data in a data frame:

        {
            "label1": (int or float, float),    -> the metric associated to the label1 and the corresponding cost (in $) in the month
            "label2": (int or float, float),    -> the metric associated to the label2 and the corresponding cost (in $) in the month
            ...
        }

        where label_i corresponds to a type of tariff in the Enum TariffType

        if monthly_detailed is set to True, the bill is detailed for each month:

        {
            "YY-MM":
            {
                "label1": (int or float, float),    -> the metric associated to the label1 and the corresponding cost (in $) in the month
                "label2": (int or float, float),    -> the metric associated to the label2 and the corresponding cost (in $) in the month
                ...
            }
        }

        :param df: a pandas dataframe containing power consumption (in W)
        :return: a dictionary representing the bill as described above
        """

        ret = {}

        # Initialize the returned structure

        t_s = df.index[0]
        t_i = datetime(t_s.year, t_s.month, 1)
        while t_i <= df.index[-1]:
            ret[t_i.strftime("%Y-%m")] = {}
            for k in self.__tariffstructures.keys():
                ret[t_i.strftime("%Y-%m")][k] = (0, 0)
            t_i += relativedelta(months=+1)

        # Compute the bill for each of the tariff type, for each month
        for label, tariff_data in self.__tariffstructures.items():
            l_blocks = self.get_tariff_struct(label, (df.index[0], df.index[-1]))  # get all the tariff blocks for this period and this tariff type
            for tariff_block in l_blocks:
                tariff_cost_list = tariff_block.compute_bill(df)  # this returns a dict of time-period pointing to tuple that contains both the metric of the bill and the cost
                for time_label, bill_data in tariff_cost_list.items():
                    self.update_bill_structure(ret[time_label], label, bill_data)

        if monthly_detailed is False:  # Aggregate all the months
            return self.aggregate_monthly_bill(ret)
        else:
            return ret

    def get_electricity_price(self, range_date, timestep):
        """

        This function creates the electricity price signal for the specified time frame 'range_date', sampled at 'timestep'
        period.

        :param range_date: a tuple (t_start, t_end) of type 'datetime', representing the period
        :param timestep: an element of TariffElemPeriod enumeration (1h, 30min or 15min), representing the sampling
        period

        :return: a tuple (pd_prices, map_prices) containing:
            - pd_prices: a pandas dataframe whose index is a datetime index and containing as many cols as there are
        type_tariffs_map elements, i.e. the same keys as in __tariffstructures
            - map_prices: a mapping between the cols label and the type of tariff (fix, energy or demand)
        """

        # Prepare the Pandas dataframe
        (start_date_price, end_date_price) = range_date
        date_list = pd.date_range(start=start_date_price, end=end_date_price, freq=str(timestep.value[0]))

        # Populate the dataframe for each label, for each period
        ret_df = None
        for label_tariff in self.__tariffstructures.keys():
            df_for_label = self.get_price_in_range(label_tariff, range_date, timestep)

            if ret_df is None:
                ret_df = df_for_label
            else:
                ret_df = pd.concat([ret_df, df_for_label], axis=1)

        return ret_df, self.type_tariffs_map

    def get_price_in_range(self, label_tariff, date_range, timestep):
        """
        TODO
        remark: doesn't work with timestep > 1h ..
        """

        # TODO: this is not optimal but code-wise it's easier to write.. and there must be a way to do it with a MAP

        # Prepare the Pandas dataframe
        (start_date_price, end_date_price) = date_range
        date_range = pd.date_range(start=start_date_price, end=end_date_price, freq=str(timestep.value[0]))
        ret_df = pd.DataFrame(index=date_range, columns=[label_tariff])

        # Select the corresponding blocks

        # Get the price for the period
        for date, row in ret_df.iterrows():
            date_range_period = pd.date_range(start=date, periods=2, freq=date.freq)
            tariff_block = self.get_tariff_struct(label_tariff, (date_range_period[0], date_range_period[1]))

            if len(tariff_block) == 0:
                continue

            tariff_block = tariff_block[0]

            price_for_this_period = tariff_block.get_price_from_timestamp(date)

            # TODO: map instead of ifs ..

            # Compute ratio to scale wrt 1h

            ratio_sel_timestep = 4.0  # supposed to be 15 min

            if timestep == TariffElemPeriod.HALFLY:
                ratio_sel_timestep = 2.0
            elif timestep == TariffElemPeriod.HOURLY:
                ratio_sel_timestep = 1.0

            tariff_metric_period = tariff_block.period_metric()

            ratio_tariff_timestep = 4.0  # supposed to be 15 min

            if tariff_metric_period == TariffElemPeriod.HALFLY:
                ratio_tariff_timestep = 2.0
            elif tariff_metric_period == TariffElemPeriod.HOURLY:
                ratio_tariff_timestep = 1.0
            elif tariff_metric_period == TariffElemPeriod.DAILY:
                ratio_tariff_timestep = 1/24.0
            elif tariff_metric_period == TariffElemPeriod.MONTHLY:
                nb_days_in_this_month = calendar.monthrange(date.year, date.month)[1]
                ratio_tariff_timestep = 1/24.0 * 1/nb_days_in_this_month

            price_scaled = price_for_this_period / ratio_sel_timestep * ratio_tariff_timestep

            ret_df.loc[date, label_tariff] = price_scaled

        return ret_df

    def print_aggregated_bill(self, bill_struct):

        monthly_detailed = False

        # If the first keys of the dict point to smth that is not the tariff type, this is a monthly bill
        first_keys_bill_struct = bill_struct.keys()
        if first_keys_bill_struct[0] not in self.__tariffstructures.keys():
            monthly_detailed = True

        if monthly_detailed is True:  # This supposes the bill is calculated per natural month of the calendar

            # Aggregation of all the months

            acc_tot = 0.0
            acc_per_chargetype = {ChargeType.FIXED: 0.0, ChargeType.ENERGY: 0.0, ChargeType.DEMAND: 0.0}
            acc_per_label = {}
            for k in self.type_tariffs_map.keys():
                acc_per_label[k] = 0.0

            for m_key, bill_per_label in bill_struct.items():
                for lab_tariff, data in bill_per_label.items():
                    acc_tot += data[1]  # second item in data is in dollar
                    acc_per_chargetype[self.type_tariffs_map[lab_tariff]] += data[1]
                    acc_per_label[lab_tariff] += data[1]
        else:

            # The bill is already aggregated for all the months

            acc_tot = 0.0
            acc_per_chargetype = {ChargeType.FIXED: 0.0, ChargeType.ENERGY: 0.0, ChargeType.DEMAND: 0.0}

            for lab_tariff, data in bill_struct.items():
                acc_tot += data[1]  # second item in data is in dollar
                acc_per_chargetype[self.type_tariffs_map[lab_tariff]] += data[1]

            acc_per_label = bill_struct

        # Total
        print("\n| Aggregated bill: {0} ($)".format(acc_tot))

        # Per type
        print("\n| Total bill per type of charge:")
        for t_key, v in acc_per_chargetype.items():
            print(" - Charge type '{0}': {1} ($)".format(str(t_key.value[0]), v))

        # Per label
        print("\n| Total bill per type or tariff:")
        for l_key, v in acc_per_label.items():
            print(" - Type '{0}': {1} ($)".format(str(l_key), v))

        return acc_tot, acc_per_chargetype, acc_per_label

    # --- Construction and internal methods

    def add_tariff(self, tariff_obj, tariff_label, tariff_type=None):
        """
        Add a tariff block structure that fell into the category "type_rate"
        :param tariff_obj: a TariffBase (or children) object
        :param tariff_label: the label of the tariff, in the keys given to the constructor
        :param tariff_type: the type of tariff, an enum of ChargeType
        :return: /
        """

        # The tariff type (fix, demand or energy) is not specified: get it from the default structure
        if tariff_type is None:
            tariff_type = tariff_label

            if tariff_label in self.DEFAULT_TARIFF_MAP.keys():
                tariff_type = self.DEFAULT_TARIFF_MAP[tariff_label]
            else:
                print "[in add_tariff] Couldn't add the tariff object:" \
                      "The tariff_type is missing and couldn't be retrieved from the label '{0}'".format(tariff_label)  # debug
                return

        # The label tariff is a new one:
        if tariff_label not in self.__tariffstructures.keys():
            self.__tariffstructures[tariff_label] = self.generate_type_tariff(tariff_type)

        self.__tariffstructures[tariff_label]['list_blocks'].append(tariff_obj)

    def get_tariff_struct(self, label_tariff, dates=None):
        """
        Get the list of "tariff blocks" that influence the bill for the type of tariff "type_rate".
        If "dates" is specified, only the blocks that are effective for that period are returned
        :param label_tariff: a string pointing to the type of tariff
        :param dates:[optional] a tuple of type datetime defining the period of selection
        :return: a list of TariffBase (or children) describing the tariffs
        """

        list_struct = self.__tariffstructures[label_tariff]['list_blocks']

        if dates is None:
            return list_struct
        else:
            (start_sel, end_sel) = dates

            return [obj for obj in list_struct if ((obj.startdate <= start_sel <= obj.enddate) or (start_sel <= obj.startdate <= end_sel))]

    def update_bill_structure(self, intermediate_monthly_bill, label_tariff, new_data):
        """
        This method update the current monthly bill with new data for the same month:
         - In case of "demand charge per (k)W", apply MAX
         - In case of "energy charge per (k)Wh or fixed cost per month", apply SUM
        :param intermediate_monthly_bill: the dict structure as return by the compute_bill() method, for a specific month key
        :param label_tariff: a string indicating the tariff. Must be a key of self.__tariffstructures
        :param new_data: a tuple (metric, cost) where:
         - metric is either a float or an int, referring to the metric that influences the cost
         - cost is a float, referring to the cost in $
        :return:
        """

        type_of_tariff = self.__tariffstructures[label_tariff]['type']

        if type_of_tariff == ChargeType.DEMAND:  # Demand: apply MAX
            if new_data[0] > intermediate_monthly_bill[label_tariff][0]:
                intermediate_monthly_bill[label_tariff] = (new_data[0], new_data[1])
        else:  # energy or fixed cost: apply SUM
            intermediate_monthly_bill[label_tariff] = (intermediate_monthly_bill[label_tariff][0] + new_data[0],
                                                       intermediate_monthly_bill[label_tariff][1] + new_data[1])

    def aggregate_monthly_bill(self, monthly_bill):
        """

        :param monthly_bill:
        :return: /
        """

        data_merge = None
        for m, data_per_label in monthly_bill.items():
            if data_merge is None:
                data_merge = data_per_label
            else:
                for label_tariff, data_tariff in data_per_label.items():
                    if self.type_tariffs_map[label_tariff] == ChargeType.DEMAND:  # take max
                        # TODO: check if it's a flat or TOU rate and take the max of each
                        # Flat rate
                        # if type(data_tariff) is
                        # TOU demand rate
                        if data_tariff[0] > data_merge[label_tariff][0]:
                            data_merge[label_tariff] = data_tariff
                    else:  # sum
                        data_merge[label_tariff] = (data_merge[label_tariff][0] + data_tariff[0],
                                                    data_merge[label_tariff][1] + data_tariff[1])

        return data_merge


    @staticmethod
    def generate_type_tariff(type_tariff):
        return {'type': type_tariff,
                'list_blocks': []}
