from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class FarmPlot:
    crop: str
    location_name: str
    latitude: float
    longtitude: float
    plot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda:datetime.now().isoformat())

    def to_dictionary(self) -> dict:
        return{
            "crop": self.crop,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longtitude": self.longtitude,
            "plot_id": self.plot_id,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dictionary(cls, data: dict) -> "FarmPlot":
        return cls(
            crop = data["crop"],
            location_name = data["location_name"],
            latitude = data["latitude"],
            longtitude = data["longtitude"],
            plot_id = data["plot_id"],
            created_at = data["created_at"]
        )


@dataclass
class LogEntry:
    plot_id: str
    date: str
    crop: str
    location_name: str
    temperature_Celcius: float
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
            "temperature_Celsius": self.temperature_Celcius,
            "humidity_pct": self.humidity_pct,
            "advice_summary": self.advice_summary
        }
         

if __name__ == "__main__":
    plot = FarmPlot(crop="maize", location_name="Nsukka", latitude=6.86, longtitude=7.40)
    print(plot)

    data = plot.to_dictionary()
    print(data)

    rebuilt = FarmPlot.from_dictionary(data)
    print(rebuilt)

    assert plot.to_dictionary() == rebuilt.to_dictionary()
    print("Round-trip works!")


    log = LogEntry(
        plot_id = plot.plot_id,
        date = "2026-08-29",
        crop = "maize",
        location_name="Nsukka",
        temperature_Celcius = 27.5,
        humidity_pct = 68.0,
        advice_summary = "Good conditions for planting.",
    )
    print(log.to_row())