from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid


# ============================================================
# Crop class + season calendar generator
# ============================================================
# The original brief calls for a "Crop" class and a season calendar
# (planting -> weeding -> harvest). Neither was assigned to anyone in
# the group's task-division doc, so it lives here in app.py.
#
# The day-counts below are typical agronomic averages for staple crops
# grown across Nigeria and similar tropical/sub-tropical regions, drawn
# from standard agricultural-extension guidance (FAO crop calendars and
# CGIAR/IITA variety guides). Real durations vary by specific variety,
# local climate, and soil — these are sensible defaults, not a
# substitute for the planting guide that comes with a specific seed
# variety.


class Crop:
    """Represents one crop's typical growth-stage timeline, in days
    counted from the planting date."""

    def __init__(self, name: str, weeding_days: list, harvest_days: int):
        self.name = name
        self.weeding_days = weeding_days  # e.g. [21, 45] -> two weeding rounds
        self.harvest_days = harvest_days  # e.g. 110 -> ready to harvest on day 110

    def build_calendar(self, planting_date) -> list:
        """
        planting_date: a datetime.date object.
        Returns a list of {"stage": str, "date": date} dicts, in order —
        planting, each weeding round, then harvest.
        """
        calendar = [{"stage": "Planting", "date": planting_date}]
        for i, days in enumerate(self.weeding_days, start=1):
            label = "Weeding" if len(self.weeding_days) == 1 else f"Weeding (round {i})"
            calendar.append({"stage": label, "date": planting_date + timedelta(days=days)})
        calendar.append({"stage": "Harvest", "date": planting_date + timedelta(days=self.harvest_days)})
        return calendar


def generate_season_calendar(crop_name: str, planting_date_str: str) -> list:
    """
    crop_name: must be a key in CROP_PROFILES (matches SUPPORTED_CROPS).
    planting_date_str: "YYYY-MM-DD" string, already validated by validate_date().
    """
    crop_obj = CROP_PROFILES.get(crop_name)
    if crop_obj is None:
        return []  # unknown crop — nothing to build a calendar from
    planting_date = datetime.strptime(planting_date_str, "%Y-%m-%d").date()
    return crop_obj.build_calendar(planting_date)

CROP_PROFILES = {
    "Maize":    Crop("Maize",    weeding_days=[21, 42],     harvest_days=110),
    "Rice":     Crop("Rice",     weeding_days=[21, 42],     harvest_days=120),
    "Cassava":  Crop("Cassava",  weeding_days=[30, 90],     harvest_days=300),
    "Yam":      Crop("Yam",      weeding_days=[30, 60, 90], harvest_days=240),
    "Sorghum":  Crop("Sorghum",  weeding_days=[21, 42],     harvest_days=105),
}



MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}



@dataclass
class FarmPlot:
    crop: str
    location_name: str
    latitude: float
    longitude: float
    plot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda:datetime.now().isoformat())

    def to_dict(self) -> dict:
        return{
            "crop": self.crop,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "plot_id": self.plot_id,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FarmPlot":
        return cls(
            crop = data["crop"],
            location_name = data["location_name"],
            latitude = data["latitude"],
            longitude = data["longitude"],
            plot_id = data["plot_id"],
            created_at = data["created_at"]
        )


@dataclass
class LogEntry:
    plot_id: str
    date: str
    crop: str
    location_name: str
    temperature_Celsius: float
    humidity_pct: float
    advice_summary: str
    log_id:  str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_row(self) -> dict:
        return {
            "log_id": self.log_id,
            "plot_id": self.plot_id,
            "date": self.date,
            "crop": self.crop,
            "location_name": self.location_name,
            "temperature_Celsius": self.temperature_Celsius,
            "humidity_pct": self.humidity_pct,
            "advice_summary": self.advice_summary
        }
         

if __name__ == "__main__":
    plot = FarmPlot(crop="maize", location_name="Nsukka", latitude=6.86, longitude=7.40)
    print(plot)

    data = plot.to_dict()
    print(data)

    rebuilt = FarmPlot.from_dict(data)
    print(rebuilt)

    assert plot.to_dict() == rebuilt.to_dict()
    print("Round-trip works!")


    log = LogEntry(
        plot_id = plot.plot_id,
        date = "2026-08-29",
        crop = "maize",
        location_name="Nsukka",
        temperature_Celsius = 27.5,
        humidity_pct = 68.0,
        advice_summary = "Good conditions for planting.",
    )
    
    print(log.to_row())