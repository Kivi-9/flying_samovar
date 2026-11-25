"""Модель самовара-аэростата «Пар-Облако»."""

from fractions import Fraction
from math import isfinite
from sys import float_info

__all__ = [
    "CrazyVehicleError",
    "FlyingSamovar",
    "SamovarEnvelopeTorn",
    "SamovarError",
    "SamovarNoEnergy",
    "SamovarNotFlying",
    "SamovarNotOnGround",
    "SamovarOverweight",
]

_MAX_ENERGY = 100.0
_ENERGY_TOLERANCE = 1e-9

# Множитель скорости и расход энергии на километр.
_WEATHER = {
    "calm": (1.0, 2.0),
    "tailwind": (1.5, 1.0),
    "headwind": (0.5, 3.0),
    "storm": (0.25, 4.0),
}


class CrazyVehicleError(Exception):
    """Базовое исключение для необычных транспортных средств."""


class SamovarError(CrazyVehicleError):
    """Базовое исключение самовара-аэростата."""


class SamovarNoEnergy(SamovarError):
    """Энергии недостаточно для действия."""


class SamovarEnvelopeTorn(SamovarError):
    """Баллон разорван."""


class SamovarOverweight(SamovarError):
    """Общая масса превышает грузоподъёмность."""


class SamovarNotFlying(SamovarError):
    """Действие возможно только в воздухе."""


class SamovarNotOnGround(SamovarError):
    """Действие возможно только на земле."""


def _require_number(value: float, parameter: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{parameter} must be an int or float")


def _finite_float(value: float, parameter: str) -> float:
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{parameter} is outside the float range") from error
    if not isfinite(number):
        raise ValueError(f"{parameter} must be finite")
    return number


def _positive_float(value: float, parameter: str) -> float:
    number = _finite_float(value, parameter)
    if number <= 0.0:
        raise ValueError(f"{parameter} must be positive")
    return number


def _flight_parameters(
    distance_km: float, weather: str
) -> tuple[float, float, float]:
    _require_number(distance_km, "distance_km")
    if not isinstance(weather, str):
        raise TypeError("weather must be a string")
    distance = _positive_float(distance_km, "distance_km")
    conditions = _WEATHER.get(weather)
    if conditions is None:
        raise ValueError(f"unknown weather: {weather!r}")
    speed_factor, energy_per_km = conditions
    return distance, speed_factor, energy_per_km


def _flight_hours(distance: float, max_speed: float, factor: float) -> float:
    speed = max_speed * factor
    if float_info.min <= speed <= float_info.max:
        return distance / speed

    # При предельной скорости сохраняем точность до вычисления частного.
    hours = Fraction(distance) / (Fraction(max_speed) * Fraction(factor))
    try:
        return float(hours)
    except OverflowError:
        return float("inf")


class FlyingSamovar:
    """Самовар-аэростат с запасом энергии, грузом и ремонтируемым баллоном."""

    def __init__(
        self,
        name: str,
        mass_kg: float,
        envelope_volume_m3: float,
        max_speed_kmh: float,
        energy: float = _MAX_ENERGY,
    ) -> None:
        """Создать аппарат на земле с целым баллоном и без груза."""
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        _require_number(mass_kg, "mass_kg")
        _require_number(envelope_volume_m3, "envelope_volume_m3")
        _require_number(max_speed_kmh, "max_speed_kmh")
        _require_number(energy, "energy")

        name = name.strip()
        if not name:
            raise ValueError("name must not be empty")
        mass = _positive_float(mass_kg, "mass_kg")
        volume = _positive_float(envelope_volume_m3, "envelope_volume_m3")
        speed = _positive_float(max_speed_kmh, "max_speed_kmh")
        fuel = _finite_float(energy, "energy")
        if not 0.0 <= fuel <= _MAX_ENERGY:
            raise ValueError("energy must be between 0 and 100")

        self._name = name
        self._mass_kg = mass
        self._envelope_volume_m3 = volume
        self._max_speed_kmh = speed
        self._energy = fuel
        self._position_km = 0.0
        self._is_flying = False
        self._envelope_intact = True
        self._load_kg = 0.0

    @property
    def name(self) -> str:
        """Имя аппарата."""
        return self._name

    @property
    def mass_kg(self) -> float:
        """Масса пустого аппарата в килограммах."""
        return self._mass_kg

    @property
    def envelope_volume_m3(self) -> float:
        """Объём баллона в кубических метрах."""
        return self._envelope_volume_m3

    @property
    def max_speed_kmh(self) -> float:
        """Скорость в штиль в километрах в час."""
        return self._max_speed_kmh

    @property
    def energy(self) -> float:
        """Текущий запас энергии в условных единицах."""
        return self._energy

    @property
    def position_km(self) -> float:
        """Суммарное пройденное расстояние в километрах."""
        return self._position_km

    @property
    def is_flying(self) -> bool:
        """Находится ли аппарат в воздухе."""
        return self._is_flying

    @property
    def envelope_intact(self) -> bool:
        """Цел ли баллон."""
        return self._envelope_intact

    @property
    def load_kg(self) -> float:
        """Масса груза на борту в килограммах."""
        return self._load_kg

    @property
    def lift_capacity_kg(self) -> float:
        """Предельная общая масса аппарата и груза в килограммах."""
        return self._envelope_volume_m3 * 0.5

    def take_off(self, cargo_kg: float = 0.0) -> None:
        """Взлететь с указанным грузом, потратив 10 единиц энергии."""
        _require_number(cargo_kg, "cargo_kg")
        cargo = _finite_float(cargo_kg, "cargo_kg")
        if cargo < 0.0:
            raise ValueError("cargo_kg must be non-negative")
        self._require_ground()
        self._require_intact_envelope()
        if self._mass_kg + cargo > self.lift_capacity_kg:
            raise SamovarOverweight("total mass exceeds lift capacity")

        self._energy = self._energy_after_spending(10.0)
        self._is_flying = True
        self._load_kg = cargo

    def fly(self, distance_km: float, weather: str) -> float:
        """Пролететь указанное расстояние и вернуть время в часах."""
        distance, speed_factor, energy_per_km = _flight_parameters(
            distance_km, weather
        )
        self._require_flight()
        self._require_intact_envelope()
        required_energy = distance * energy_per_km
        remaining_energy = self._energy_after_spending(required_energy)
        hours = _flight_hours(distance, self._max_speed_kmh, speed_factor)

        self._position_km += distance
        self._energy = remaining_energy
        if weather == "storm":
            self._envelope_intact = False
        return hours

    def land(self) -> None:
        """Приземлиться и освободить аппарат от груза."""
        self._require_flight()
        self._is_flying = False
        self._load_kg = 0.0

    def can_overcome(self, obstacle: str) -> bool:
        """Проверить препятствие по состоянию полёта, энергии или объёму."""
        if not isinstance(obstacle, str):
            raise TypeError("obstacle must be a string")
        if obstacle == "tree":
            return self._is_flying
        if obstacle == "mountain":
            return self._is_flying and self._energy > 30.0
        if obstacle == "gorge":
            return self._envelope_volume_m3 <= 500.0
        raise ValueError(f"unknown obstacle: {obstacle!r}")

    def calculate_energy(self, distance_km: float, weather: str) -> float:
        """Вернуть затраты на перелёт без изменения состояния аппарата."""
        distance, _, energy_per_km = _flight_parameters(distance_km, weather)
        return distance * energy_per_km

    def refuel(self, amount: float) -> None:
        """Заправиться на земле до предела в 100 единиц энергии."""
        _require_number(amount, "amount")
        fuel = _positive_float(amount, "amount")
        self._require_ground()
        self._energy = min(_MAX_ENERGY, self._energy + fuel)

    def damage_envelope(self) -> None:
        """Разорвать баллон, оставаясь в текущем состоянии полёта."""
        self._envelope_intact = False

    def repair_envelope(self) -> None:
        """Починить разорванный баллон на земле за 15 единиц энергии."""
        self._require_ground()
        if self._envelope_intact:
            return
        self._energy = self._energy_after_spending(15.0)
        self._envelope_intact = True

    def get_status(self) -> dict[str, str | float | bool]:
        """Вернуть независимый снимок состояния аппарата."""
        return {
            "name": self._name,
            "energy": self._energy,
            "position_km": self._position_km,
            "is_flying": self._is_flying,
            "envelope_intact": self._envelope_intact,
            "load_kg": self._load_kg,
        }

    def _require_flight(self) -> None:
        if not self._is_flying:
            raise SamovarNotFlying("samovar is on the ground")

    def _require_ground(self) -> None:
        if self._is_flying:
            raise SamovarNotOnGround("samovar is in flight")

    def _require_intact_envelope(self) -> None:
        if not self._envelope_intact:
            raise SamovarEnvelopeTorn("envelope is torn")

    def _energy_after_spending(self, required: float) -> float:
        if required > self._energy + _ENERGY_TOLERANCE:
            raise SamovarNoEnergy(
                f"required {required}, available {self._energy}"
            )
        return max(0.0, self._energy - required)
