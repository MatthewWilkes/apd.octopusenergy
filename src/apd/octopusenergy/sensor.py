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
    name = "OctopusPowerUsage"
    title = "Power Usage"

    def __init__(
        self, api_key="", serial="", mpan=""
    ) -> None:
        self.api_key = os.environ.get(
            "APD_OCTOPUS_API_KEY", api_key
        )
        self.mpan = os.environ.get(
            "APD_OCTOPUS_MPAN", mpan
        )
        self.serial = os.environ.get(
            "APD_OCTOPUS_SERIAL", serial
        )

    def value(self) -> t.Optional[t.Any]:
        raise PersistentSensorFailureError("Only historical data is available")
    
    def historical(
        self, start: datetime.datetime, end: datetime.datetime
    ) -> t.Iterable[t.Tuple[datetime.datetime, t.Any]]:
        start = start.replace(microsecond=0)
        end = end.replace(microsecond=0)
        url = f"https://api.octopus.energy/v1/electricity-meter-points/{self.mpan}/meters/{self.serial}/consumption/?period_from={start.isoformat()}&period_end={end.isoformat()}&page_size=25000"
        data = requests.get(url, auth=(self.api_key, ""))
        for item in data.json()["results"]:
            yield datetime.datetime.fromisoformat(item["interval_end"].strip("Z")), ureg.Quantity(item["consumption"]*2, "kilowatthours")
    
    @classmethod
    def format(cls, value: t.Any) -> str:
        return "{:~P}".format(value.to(ureg.kilowatt))

    @classmethod
    def to_json_compatible(cls, value: t.Any) -> t.Dict[str, t.Union[str, float]]:
        return {"magnitude": value.magnitude, "unit": str(value.units)}

    @classmethod
    def from_json_compatible(cls, json_version: t.Any) -> t.Any:
        return ureg.Quantity(json_version["magnitude"], ureg[json_version["unit"]])