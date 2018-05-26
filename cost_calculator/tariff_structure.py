__author__ = 'Olivier Van Cutsem'

from abc import abstractmethod
from enum import Enum
from datetime import datetime
import calendar
import pandas as pd

# --------------- TARIFF structures --------------- #


class TariffType(Enum):
    FIX_CUSTOM_CHARGE = 'customer_fix_charge',
    ENERGY_CUSTOM_CHARGE = 'customer_energy_charge',
    DEMAND_CUSTOM_CHARGE_SEASON = 'customer_demand_charge_season',
    DEMAND_CUSTOM_CHARGE_TOU = 'customer_demand_charge_tou',
    FIX_DREVENT_CHARGE = 'dr_event_fix_charge',
    ENERGY_DREVENT_CHARGE = 'dr_event_energy_charge',
    DEMAND_DREVENT_CHARGE = 'dr_event_demand_charge',


class TariffElemPeriod(Enum):

    MONTHLY = 'M',
    DAILY = 'D',
    HOURLY = '1h',
    HALFLY = '30min',
    QUARTERLY = '15min',


class TariffElemMetricUnit(Enum):
    EN_WH = 1,
    DEMAND_W = 1,
    EN_KWH = 1000.0,
    DEMAND_KW = 1000.0,


class TariffElemCostUnit(Enum):
    CENT = 0.01,
    DOLLAR = 1,


class TariffBase(object):
    """
    This abstract class represent the base of any tariffication structure.
    The main components are the starting and ending date of the structure.
    """

    def __init__(self, dates, unit_cost, name=None):

        # Starting and ending dates, as timestamps
        ts, te = dates
        self.__startdate = ts
        self.__enddate = te

        self.name = name
        self.unit_cost = unit_cost

    def compute_bill(self, df):
        """
        Compute the bill due to the power/energy consumption in df, for each billing period specified in billing_periods

        It outputs a dictionary formatted as follow:
        {
            "bill_period_label1": (float or dict, float),     -> the monthly 'metric' and its cost
            ...
        }

        :param df: a pandas dataframe containing power consumption timeseries
        :param billing_periods: a dictionary mapping the billing periods label to a tuple (t_start, t_end) of datetime,
        defining the period related to the billing label
        :return: a dictionary formatted as in this method signature
        """

        ret = {}

        # Select only the data in this tariff window

        # mask = (df.index >= self.startdate) & (df.index <= self.enddate)
        # df = df.loc[mask]

        # Loop over the months
        t_s = df.index[0]
        last_day_of_month = calendar.monthrange(t_s.year, t_s.month)[1]  # The last day of this month
        t_e = datetime(t_s.year, t_s.month, last_day_of_month, hour=23, minute=59, second=59)  # end of the current month
        t_e = min(df.index[-1], t_e)

        while t_s <= t_e:
            mask = (df.index >= t_s) & (df.index <= t_e)
            df_month = df.loc[mask]
            monthly_bill = self.compute_monthly_bill(df_month)
            ret[t_s.strftime("%Y-%m")] = monthly_bill

            # Prepare the next billing month
            month = t_e.month + 1
            year = t_e.year
            if month >= 13:
                month = 1
                year += 1

            t_s = datetime(year, month, 1, hour=0, minute=0, second=0)

            last_day_of_month = calendar.monthrange(year, month)[1]
            t_e = datetime(year, month, last_day_of_month, hour=23, minute=59, second=59)
            t_e = min(df.index[-1], t_e)

        return ret

    @abstractmethod
    def compute_monthly_bill(self, df):
        """
        Compute the monthly bill due to the power/energy consumption in df
        :param df: a pandas dataframe
        :param param: an additional set of parameters
        :return: a tuple (float, float) -> (value, cost), representing the bill and the corresponding metric linked to the cost
        """

        pass

    @property
    def startdate(self):
        """
        GETTER of the tariff starting date
        :return: a timestamp
        """

        return self.__startdate

    @property
    def enddate(self):
        """
        GETTER of the tariff end date
        :return: a timestamp
        """

        return self.__enddate

    @abstractmethod
    def period_metric(self):
        pass

    @abstractmethod
    def get_price_from_timestamp(self, timestamp):
        pass


# --------------- FIXED TARIFF --------------- #


class FixedTariff(TariffBase):
    """
    Represent a tariff fixed over a given period (among TariffPeriod)
    """

    def __init__(self, dates, rate_value, unit_cost=TariffElemCostUnit.DOLLAR, bill_period=TariffElemPeriod.MONTHLY, name=None):
        """
        Constructor
        :param dates: see FixedTariff init
        :param bill_period: the period
        :param name: see FixedTariff init
        """

        super(FixedTariff, self).__init__(dates, unit_cost, name)

        self.__rate_period = bill_period
        self.__rate_value = rate_value

    def compute_monthly_bill(self, df):
        """
        Compute the monthly bill due to a fixed periodic cost

        :param df: a pandas dataframe
        :return: a tuple (float, float), representing the bill and the duration (in months)
        """
        first_day = df.index[0].day
        last_day = df.index[-1].day

        nb_days = last_day - first_day + 1

        bill = 0
        if self.__rate_period == TariffElemPeriod.MONTHLY:
            bill = self.__rate_value * nb_days/last_day  # a fraction of the month
        elif self.__rate_period == TariffElemPeriod.DAILY:
            bill = self.__rate_value * nb_days  # sum of each day

        return nb_days, bill

    def period_metric(self):
        return self.__rate_period

    def get_price_from_timestamp(self, timestamp):
        return self.__rate_value

# TODO: float demand class

# --------------- TOU TARIFFs --------------- #


class TimeOfUseTariff(TariffBase):
    """
    This class represents a tariff fixed over a given period (among TariffElemPeriod)
    """

    def __init__(self, dates, rate_schedule, unit_metric, unit_cost, name=None):
        """
        Constructor
        :param dates: see FixedTariff init
        :param rate_list:
        :param time_schedule: TODO
        :param name: see FixedTariff init
        """

        super(TimeOfUseTariff, self).__init__(dates, unit_cost, name)

        self.__schedule = rate_schedule  # A table mapping (month, day) to hourly rate index
        self.__unit_metric = unit_metric

    @abstractmethod
    def compute_monthly_bill(self, df):
        """
        idem super
        """

        pass

    @property
    def rate_schedule(self):
        return self.__schedule

    @property
    def unit_metric(self):
        return self.__unit_metric

    def period_metric(self):
        # TODO: replace ifs by map
        nb_periods_in_day = self.__schedule.periods_in_day

        if nb_periods_in_day == 24:
            return TariffElemPeriod.HOURLY
        elif nb_periods_in_day == 24 * 2:
            return TariffElemPeriod.HALFLY
        elif nb_periods_in_day == 24 * 4:
            return TariffElemPeriod.QUARTERLY
        else:
            return TariffElemPeriod.DAILY

    def get_price_from_timestamp(self, timestamp):
        # TODO: scale with the unit
        return self.__schedule.get_from_timestamp(timestamp)


class TouDemandChargeTariff(TimeOfUseTariff):
    """
    This class represents a Time Of Use Demand Charge tariff
    """

    def __init__(self, dates, time_schedule, unit_metric=TariffElemMetricUnit.DEMAND_KW, unit_cost=TariffElemCostUnit.DOLLAR, name=None):
        """
        Constructor
        :param dates: see FixedTariff init
        :param rate_list: TODO
        :param time_schedule: TODO
        :param name: see FixedTariff init
        """

        super(TouDemandChargeTariff, self).__init__(dates, time_schedule, unit_metric, unit_cost, name)

    def compute_monthly_bill(self, df):
        """
        Compute the bill due to a TOU tariff
        :param df: a pandas dataframe
        :return: a tuple (dict, float) -> ({p1: (max_power_p1, time_max_p1), p2: (max_power_p2, time_max_p2), cost)
        """

        # Scaling the power unit and cost
        metric_unit_mult = float(self.unit_metric.value[0])
        metric_price_mult = float(self.unit_cost.value[0])

        # TODO check the period of the data ! It has been assumed that mean(P_per) = E_per
        # The logic is to get the TOU demand price and split it in different periods, according to the price values
        set_of_monthly_prices = set()
        max_per_set = {}

        for idx, df_day in df.groupby(df.index.date):

            daily_rate = self.rate_schedule.get_daily_rate(df_day.index[0])

            set_of_daily_prices = set(daily_rate)
            for p in set_of_daily_prices:
                if p > 0 and p not in set_of_monthly_prices:  # A new price that hasn't yet been seen
                    set_of_monthly_prices.add(p)
                    max_per_set[p] = (0, 0)

            # Constructing the dataframe for an easier manipulation of time
            period_rate = len(daily_rate) / 24.0

            # TODO: remove if's ...
            freq_per = '1h'
            if period_rate == 1: # 1 hour
                freq_per = '1h'
            elif period_rate == 2:
                freq_per = '30min'
            elif period_rate == 4:
                freq_per = '15min'

            # The first day may be incomplete
            first_idx = (df_day.index[0].hour + df_day.index[0].minute/60.0) * period_rate

            # The last day may be incomplete
            last_idx = (df_day.index[-1].hour + df_day.index[-1].minute/60.0) * period_rate

            data = {'date': df_day.asfreq(freq=freq_per).index, 'price': daily_rate[int(first_idx):int(last_idx)+1]}

            df_prices = pd.DataFrame(data=data)

            for p in set_of_daily_prices:

                # select the indexes for this price
                mask_price = df_prices[df_prices['price'] == p].index
                date_max_period = df[mask_price].idxmax()
                max_power_period = df[date_max_period]
                if max_power_period > max_per_set[p][0]:
                    max_per_set[p] = (max_power_period / metric_unit_mult, date_max_period.to_pydatetime())

        # Sum costs per periods
        cost_tot = metric_price_mult * sum([p * v[0] for p, v in max_per_set.items()])

        return max_per_set, cost_tot


class TouEnergyChargeTariff(TimeOfUseTariff):
    """
    This class represents a Time Of Use Energy Charge tariff
    """

    def __init__(self, dates, time_schedule, unit_metric=TariffElemMetricUnit.EN_KWH, unit_cost=TariffElemCostUnit.DOLLAR, name=None):
        """
        Constructor
        :param dates: see FixedTariff init
        :param time_schedule: TODO
        :param name: see FixedTariff init
        """

        super(TouEnergyChargeTariff, self).__init__(dates, time_schedule, unit_metric, unit_cost, name)

    def compute_monthly_bill(self, df):
        """
        Compute the bill due to a TOU tariff
        :param df: a pandas dataframe
        :return: a tuple (float, float) -> (cost, tot_energy)
        """

        # Iterates over the days
        energy = 0.0
        cost = 0.0

        # TODO: check for blockrate !

        for idx, day in df.groupby(df.index.date):

            daily_rate = self.rate_schedule.get_daily_rate(day.index[0])
            period = len(daily_rate) / 24.0

            # TODO: remove if's ...
            freq_per = '1h'
            if period == 1: # 1 hour
                freq_per = '1h'
            elif period == 2:
                freq_per = '30min'
            elif period == 4:
                freq_per = '15min'

            df_day = day.asfreq(freq=freq_per)

            # The first month may be incomplete
            first_idx = (df_day.index[0].hour + df_day.index[0].minute/60.0) * period

            # The last month may be incomplete
            last_idx = (df_day.index[-1].hour + df_day.index[-1].minute/60.0) * period

            # Unit and cost scale
            mult_energy_unit = float(self.unit_metric.value[0])
            mult_cost_unit = float(self.unit_cost.value[0])

            # Cumulate the energy over the month
            energy += sum(df_day[:]) / mult_energy_unit

            # Cumulate the bill over the month
            cost += sum(mult_cost_unit * df_day.multiply(daily_rate[int(first_idx):int(last_idx)+1])) / mult_energy_unit

        return energy, cost
