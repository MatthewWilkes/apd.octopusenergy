import datetime
import os
import subprocess
import requests
import typing as t

from pint import _DEFAULT_REGISTRY as ureg

from apd.sensors.base import Sensor
from apd.sensors.exceptions import (
    PersistentSensorFailureError,
    IntermittentSensorFailureError,
)

class OctopusPowerUsage(Sensor[t.Any]):

    def value(self) -> t.Optional[t.Any]:
        raise PersistentSensorFailureError("Only historical data is available")
    
    def historical(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> t.Iterable[t.Tuple[datetime.datetime, t.Any]]:
        start = start.replace(microsecond=0)
        end = end.replace(microsecond=0)
        url = f"https://api.octopus.energy/v1/{self.fuel}-meter-points/{self.mpan}/meters/{self.serial}/consumption/?period_from={start.isoformat()}&period_end={end.isoformat()}&page_size=25000"
        data = requests.get(url, auth=(self.api_key, ""))
        for item in data.json()["results"]:
            yield datetime.datetime.fromisoformat(item["interval_end"].strip("Z")), ureg.Quantity(item["consumption"], self.unit)
    
    @classmethod
    def format(cls, value: t.Any) -> str:
        return "{:~P}".format(value.to(ureg[self.unit]))

    @classmethod
    def to_json_compatible(cls, value: t.Any) -> t.Dict[str, t.Union[str, float]]:
        return {"magnitude": value.magnitude, "unit": str(value.units)}

    @classmethod
    def from_json_compatible(cls, json_version: t.Any) -> t.Any:
        return ureg.Quantity(json_version["magnitude"], ureg[json_version["unit"]])
        
class OctopusElectricityUsage(OctopusPowerUsage):
    name = "OctopusElectricityUsage"
    title = "Electricty Usage"
    fuel = "electricity"
    unit = "kilowatthours"

    def __init__(
        self, api_key="", serial="", mpan=""
    ) -> None:
        self.api_key = os.environ.get(
            "APD_OCTOPUS_API_KEY", api_key
        )
        self.mpan = os.environ.get(
            "APD_OCTOPUS_ELECTRICITY_MPAN", mpan
        )
        self.serial = os.environ.get(
            "APD_OCTOPUS_ELECTRICITY_SERIAL", serial
        )

class OctopusGasUsage(OctopusPowerUsage):
    name = "OctopusGasUsage"
    title = "Gas Usage"
    fuel = "gas"

    def __init__(
        self, api_key="", serial="", mpan="", unit=None,
    ) -> None:
        self.api_key = os.environ.get(
            "APD_OCTOPUS_API_KEY", api_key
        )
        self.mpan = os.environ.get(
            "APD_OCTOPUS_GAS_MPAN", mpan
        )
        self.serial = os.environ.get(
            "APD_OCTOPUS_GAS_SERIAL", serial
        )
        self.unit = os.environ.get(
            "APD_OCTOPUS_GAS_UNIT", unit
        )
        if unit is None:
            unit = "kilowatthours"


class OctopusElectricityPricing(OctopusPowerUsage):
    name = "OctopusElectricityPricing"
    title = "Electricity Price"

    def __init__(
        self, api_key="", account=""
    ) -> None:
        self.api_key = os.environ.get(
            "APD_OCTOPUS_API_KEY", api_key
        )
        self.account = os.environ.get(
            "APD_OCTOPUS_ACCOUNT_NUMBER", account
        )

    def value(self) -> t.Optional[t.Any]:
        raise PersistentSensorFailureError("Only historical data is available")
    
    def historical(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> t.Iterable[t.Tuple[datetime.datetime, t.Any]]:
        start = start.replace(microsecond=0)
        end = end.replace(microsecond=0)
        url = f"https://api.octopus.energy/v1/accounts/{self.account}/"
        data = requests.get(url, auth=(self.api_key, "")).json()
        
        try:
            tariff = data["properties"][0]["electricity_meter_points"][0]["agreements"][-1]["tariff_code"]
        except (IndexError, KeyError) as e:
            raise IntermittentSensorFailureError("Could not determine tariff")
        
        product = "-".join(tariff.split("-")[2:-1])
        
        url = f"https://api.octopus.energy/v1/products/{product}/electricity-tariffs/{tariff}/standard-unit-rates/?period_from={start.isoformat()}&period_end={end.isoformat()}&page_size=25000"
        data = requests.get(url, auth=(self.api_key, "")).json()
        
        for item in data["results"]:
            yield datetime.datetime.fromisoformat(item["valid_to"].strip("Z")), ((item["value_inc_vat"] / 100) / ureg.kilowatthours)
    
    @classmethod
    def format(cls, value: t.Any) -> str:
        return "{:~P}".format(value.to(ureg[self.unit]))

    @classmethod
    def to_json_compatible(cls, value: t.Any) -> t.Dict[str, t.Union[str, float]]:
        return {"magnitude": value.magnitude, "unit": str(value.units)}

    @classmethod
    def from_json_compatible(cls, json_version: t.Any) -> t.Any:
        return ureg.Quantity(json_version["magnitude"], ureg[json_version["unit"]])
