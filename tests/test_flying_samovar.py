"""Тесты класса FlyingSamovar — самовара-аэростата «Пар-Облако».

Автор ТЗ и тестов (роль A): Сергеев Максим Витальевич, БСБО-16-23.
Источник правды: SPEC.md и TEST_CASES.md. ID каждого тест-кейса указан
в имени и в docstring теста.

Модульные тесты (TC-01 … TC-19) написаны по паттерну AAA, сценарные
(TC-20 … TC-23) — по паттерну Given-When-Then через тестовую обёртку Pilot.

Запуск из корня репозитория:
    python -m unittest discover -s tests -t . -v
"""
import unittest

from flying_samovar import (
    CrazyVehicleError,
    FlyingSamovar,
    SamovarEnvelopeTorn,
    SamovarError,
    SamovarNoEnergy,
    SamovarNotFlying,
    SamovarNotOnGround,
    SamovarOverweight,
)

NAN = float("nan")
INF = float("inf")
PLACES = 9  # допуск сравнения вещественных чисел (SPEC, раздел 3)

NUMERIC_PARAMS = ("mass_kg", "envelope_volume_m3", "max_speed_kmh")
PUBLIC_ATTRIBUTES = (
    "name",
    "mass_kg",
    "envelope_volume_m3",
    "max_speed_kmh",
    "energy",
    "position_km",
    "is_flying",
    "envelope_intact",
    "load_kg",
    "lift_capacity_kg",
)


# --------------------------------------------------------------------------
# Вспомогательные средства
# --------------------------------------------------------------------------
def make(*, name="Пар-Облако", mass_kg=120, envelope_volume_m3=400,
         max_speed_kmh=40, energy=100):
    """Базовая конфигурация: масса 120 кг, баллон 400 м³ (грузоподъёмность 200 кг)."""
    return FlyingSamovar(
        name=name,
        mass_kg=mass_kg,
        envelope_volume_m3=envelope_volume_m3,
        max_speed_kmh=max_speed_kmh,
        energy=energy,
    )


def flying(**kwargs):
    """Базовая конфигурация, уже поднявшаяся в воздух (energy уменьшена на 10)."""
    samovar = make(**kwargs)
    samovar.take_off()
    return samovar


def snapshot(samovar):
    """Снимок изменяемого состояния по публичным атрибутам."""
    return (
        samovar.energy,
        samovar.position_km,
        samovar.is_flying,
        samovar.envelope_intact,
        samovar.load_kg,
    )


class Pilot:
    """Эмулятор пилота-чаевода: управляет самоваром на доменном языке."""

    def __init__(self, samovar):
        self.самовар = samovar

    def взлететь(self, груз_кг=0.0):
        return self.самовар.take_off(груз_кг)

    def лететь(self, км, погода):
        return self.самовар.fly(км, погода)

    def сесть(self):
        return self.самовар.land()

    def заправиться(self, единиц):
        return self.самовар.refuel(единиц)

    def чинить_баллон(self):
        return self.самовар.repair_envelope()

    def проверить_препятствие(self, препятствие):
        return self.самовар.can_overcome(препятствие)


class SamovarTestCase(unittest.TestCase):
    def assert_fails_atomically(self, exception, samovar, call, *args):
        """Вызов поднимает exception, а состояние самовара не меняется."""
        before = snapshot(samovar)
        with self.assertRaises(exception):
            call(*args)
        self.assertEqual(snapshot(samovar), before)


# --------------------------------------------------------------------------
# Модульные тесты (AAA)
# --------------------------------------------------------------------------
class ConstructorTests(SamovarTestCase):
    def test_TC_01_constructor_valid_and_initial_state(self):
        """TC-01: корректные параметры, значения по умолчанию, обрезка имени."""
        # Arrange / Act
        samovar = FlyingSamovar("Пар-Облако", 120, 400, 40, 80)
        # Assert: значения и начальное состояние
        self.assertEqual(samovar.name, "Пар-Облако")
        self.assertEqual(samovar.mass_kg, 120.0)
        self.assertEqual(samovar.envelope_volume_m3, 400.0)
        self.assertEqual(samovar.max_speed_kmh, 40.0)
        self.assertEqual(samovar.energy, 80.0)
        self.assertEqual(samovar.lift_capacity_kg, 200.0)
        self.assertEqual(samovar.position_km, 0.0)
        self.assertIs(samovar.is_flying, False)
        self.assertIs(samovar.envelope_intact, True)
        self.assertEqual(samovar.load_kg, 0.0)
        # Assert: числа хранятся как float, даже если переданы int
        for attr in ("mass_kg", "envelope_volume_m3", "max_speed_kmh",
                     "energy", "lift_capacity_kg", "position_km", "load_kg"):
            with self.subTest(attr=attr):
                self.assertIsInstance(getattr(samovar, attr), float)
        # Assert: энергия по умолчанию
        default = FlyingSamovar("Чайник", 1, 1, 1)
        self.assertEqual(default.energy, 100.0)
        self.assertIsInstance(default.energy, float)
        # Assert: имя сохраняется без пробелов по краям
        padded = FlyingSamovar("  Пар-Облако \t", 120, 400, 40)
        self.assertEqual(padded.name, "Пар-Облако")

    def test_TC_02_constructor_invalid_values(self):
        """TC-02: недопустимые значения аргументов конструктора -> ValueError."""
        base = dict(name="Пар-Облако", mass_kg=120, envelope_volume_m3=400,
                    max_speed_kmh=40, energy=100)
        for param in NUMERIC_PARAMS:
            for bad in (0, -1, -0.5, NAN, INF, -INF):
                with self.subTest(param=param, value=bad):
                    # Arrange
                    kwargs = dict(base, **{param: bad})
                    # Act / Assert
                    with self.assertRaises(ValueError):
                        FlyingSamovar(**kwargs)
        for bad_name in ("", "   ", "\t\n"):
            with self.subTest(name=bad_name):
                with self.assertRaises(ValueError):
                    FlyingSamovar(**dict(base, name=bad_name))
        for bad_energy in (-0.1, 100.1, NAN, INF, -INF):
            with self.subTest(energy=bad_energy):
                with self.assertRaises(ValueError):
                    FlyingSamovar(**dict(base, energy=bad_energy))
        # граничные значения энергии допустимы
        for ok_energy in (0, 100):
            with self.subTest(energy=ok_energy):
                self.assertEqual(make(energy=ok_energy).energy, float(ok_energy))

    def test_TC_03_constructor_wrong_types(self):
        """TC-03: аргументы неверного типа (включая bool и None) -> TypeError."""
        base = dict(name="Пар-Облако", mass_kg=120, envelope_volume_m3=400,
                    max_speed_kmh=40, energy=100)
        for bad in (123, None, 1.5, b"x", ["a"]):
            with self.subTest(param="name", value=bad):
                with self.assertRaises(TypeError):
                    FlyingSamovar(**dict(base, name=bad))
        for param in NUMERIC_PARAMS:
            for bad in ("5", None, True, False, [1]):
                with self.subTest(param=param, value=bad):
                    with self.assertRaises(TypeError):
                        FlyingSamovar(**dict(base, **{param: bad}))
        for bad in ("50", None, True, False):
            with self.subTest(param="energy", value=bad):
                with self.assertRaises(TypeError):
                    FlyingSamovar(**dict(base, energy=bad))

    def test_TC_04_public_attributes_are_read_only(self):
        """TC-04: присваивание любому публичному атрибуту -> AttributeError."""
        new_values = {
            "name": "Другое", "mass_kg": 1.0, "envelope_volume_m3": 1.0,
            "max_speed_kmh": 1.0, "energy": 1.0, "position_km": 1.0,
            "is_flying": True, "envelope_intact": False, "load_kg": 1.0,
            "lift_capacity_kg": 1.0,
        }
        for attr in PUBLIC_ATTRIBUTES:
            with self.subTest(attr=attr):
                # Arrange
                samovar = make()
                before = getattr(samovar, attr)
                # Act / Assert
                with self.assertRaises(AttributeError):
                    setattr(samovar, attr, new_values[attr])
                self.assertEqual(getattr(samovar, attr), before)


class TakeOffTests(SamovarTestCase):
    def test_TC_05_take_off_success_and_boundaries(self):
        """TC-05: успешный взлёт, значение cargo_kg по умолчанию, граничные значения."""
        # (a) без груза (аргумент по умолчанию)
        samovar = make()
        result = samovar.take_off()
        self.assertIsNone(result)
        self.assertIs(samovar.is_flying, True)
        self.assertEqual(samovar.energy, 90.0)
        self.assertEqual(samovar.load_kg, 0.0)
        self.assertEqual(samovar.position_km, 0.0)
        # (b) с грузом; int-груз переводится во float
        samovar = make()
        samovar.take_off(60)
        self.assertIs(samovar.is_flying, True)
        self.assertEqual(samovar.load_kg, 60.0)
        self.assertIsInstance(samovar.load_kg, float)
        self.assertEqual(samovar.energy, 90.0)
        # (c) явный нулевой груз допустим
        samovar = make()
        samovar.take_off(0)
        self.assertIs(samovar.is_flying, True)
        self.assertEqual(samovar.load_kg, 0.0)
        # (d) граница по массе: 120 + 80 == 200 == lift_capacity_kg
        samovar = make()
        samovar.take_off(80)
        self.assertIs(samovar.is_flying, True)
        self.assertEqual(samovar.load_kg, 80.0)
        # (e) граница по энергии: ровно 10 единиц -> энергия 0
        samovar = make(energy=10)
        samovar.take_off()
        self.assertIs(samovar.is_flying, True)
        self.assertEqual(samovar.energy, 0.0)

    def test_TC_06_take_off_errors_keep_state(self):
        """TC-06: ошибки взлёта и неизменность состояния."""
        # (a) перегруз: 120 + 80.1 > 200 и сценарий 3 из SPEC 4.1 (81 кг)
        for cargo in (80.1, 81, 1e9):
            with self.subTest(overweight=cargo):
                samovar = make()
                self.assert_fails_atomically(SamovarOverweight, samovar,
                                             samovar.take_off, cargo)
        # (b) не хватает энергии: 9.9 < 10
        samovar = make(energy=9.9)
        self.assert_fails_atomically(SamovarNoEnergy, samovar, samovar.take_off)
        # (c) баллон повреждён
        samovar = make()
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarEnvelopeTorn, samovar, samovar.take_off)
        # (d) уже в воздухе
        samovar = flying()
        self.assert_fails_atomically(SamovarNotOnGround, samovar, samovar.take_off)
        # (e) некорректное значение груза -> ValueError
        for bad in (-1, -0.1, NAN, INF, -INF):
            with self.subTest(cargo=bad):
                samovar = make()
                self.assert_fails_atomically(ValueError, samovar,
                                             samovar.take_off, bad)
        # (f) груз неверного типа -> TypeError
        for bad in ("5", True, False, None, [1]):
            with self.subTest(cargo=bad):
                samovar = make()
                self.assert_fails_atomically(TypeError, samovar,
                                             samovar.take_off, bad)

    def test_TC_07_take_off_check_priority(self):
        """TC-07: порядок проверок взлёта: аргументы > не на земле > баллон > перегруз > энергия."""
        # (a) ValueError/TypeError раньше SamovarNotOnGround
        samovar = flying()
        self.assert_fails_atomically(ValueError, samovar, samovar.take_off, -1)
        self.assert_fails_atomically(TypeError, samovar, samovar.take_off, "5")
        # (b) SamovarNotOnGround раньше SamovarEnvelopeTorn
        samovar = flying()
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarNotOnGround, samovar, samovar.take_off)
        # (c) SamovarEnvelopeTorn раньше SamovarOverweight
        samovar = make()
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarEnvelopeTorn, samovar,
                                     samovar.take_off, 100)
        # (d) SamovarOverweight раньше SamovarNoEnergy
        samovar = make(energy=5)
        self.assert_fails_atomically(SamovarOverweight, samovar,
                                     samovar.take_off, 100)


class FlyTests(SamovarTestCase):
    def test_TC_08_fly_calm_tailwind_headwind(self):
        """TC-08: время, расход энергии и позиция при штиле, попутном и встречном ветре."""
        cases = (
            # погода, ожидаемое время (ч), ожидаемая энергия после 20 км
            ("calm", 20 / 40, 50.0),       # скорость 40, 2 ед/км
            ("tailwind", 20 / 60, 70.0),   # скорость 60, 1 ед/км
            ("headwind", 20 / 20, 30.0),   # скорость 20, 3 ед/км
        )
        for weather, expected_time, expected_energy in cases:
            with self.subTest(weather=weather):
                # Arrange
                samovar = flying(max_speed_kmh=40)  # energy == 90
                # Act
                elapsed = samovar.fly(20, weather)
                # Assert
                self.assertIsInstance(elapsed, float)
                self.assertAlmostEqual(elapsed, expected_time, places=PLACES)
                self.assertAlmostEqual(samovar.energy, expected_energy, places=PLACES)
                self.assertAlmostEqual(samovar.position_km, 20.0, places=PLACES)
                self.assertIs(samovar.is_flying, True)
                self.assertIs(samovar.envelope_intact, True)
        # Дробная дистанция: 2.5 км при штиле
        samovar = flying(max_speed_kmh=40)
        elapsed = samovar.fly(2.5, "calm")
        self.assertAlmostEqual(elapsed, 0.0625, places=PLACES)
        self.assertAlmostEqual(samovar.energy, 85.0, places=PLACES)
        # Позиция и расход накапливаются между вызовами
        samovar = flying(max_speed_kmh=40)
        samovar.fly(20, "calm")
        samovar.fly(10, "calm")
        self.assertAlmostEqual(samovar.position_km, 30.0, places=PLACES)
        self.assertAlmostEqual(samovar.energy, 30.0, places=PLACES)
        # Сценарий 1 из SPEC 4.1: скорость 60, 30 км при штиле
        samovar = flying(max_speed_kmh=60)
        elapsed = samovar.fly(30, "calm")
        self.assertAlmostEqual(elapsed, 0.5, places=PLACES)
        self.assertAlmostEqual(samovar.position_km, 30.0, places=PLACES)
        self.assertAlmostEqual(samovar.energy, 30.0, places=PLACES)
        self.assertIs(samovar.is_flying, True)

    def test_TC_09_fly_storm_tears_envelope(self):
        """TC-09: буря: скорость x0.25, 4 ед/км, баллон разорван после успешного перелёта."""
        # Arrange
        samovar = flying(max_speed_kmh=40, energy=100)  # energy == 90
        # Act
        elapsed = samovar.fly(10, "storm")
        # Assert
        self.assertAlmostEqual(elapsed, 1.0, places=PLACES)  # скорость 10 км/ч
        self.assertAlmostEqual(samovar.energy, 50.0, places=PLACES)
        self.assertAlmostEqual(samovar.position_km, 10.0, places=PLACES)
        self.assertIs(samovar.envelope_intact, False)
        self.assertIs(samovar.is_flying, True)
        # Энергии ровно хватает: после взлёта 40, бурей 10 км -> 0
        samovar = flying(energy=50)
        samovar.fly(10, "storm")
        self.assertEqual(samovar.energy, 0.0)
        self.assertIs(samovar.envelope_intact, False)

    def test_TC_10_fly_state_errors_and_energy_boundary(self):
        """TC-10: fly в неподходящем состоянии, граница энергии, переполнение."""
        # (a) на земле
        samovar = make()
        self.assert_fails_atomically(SamovarNotFlying, samovar,
                                     samovar.fly, 10, "calm")
        # (b) в воздухе с разорванным баллоном
        samovar = flying()
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarEnvelopeTorn, samovar,
                                     samovar.fly, 1, "calm")
        # (c) энергии хватает ровно (20 ед.), затем следующий перелёт невозможен
        samovar = flying(energy=30)  # energy == 20
        samovar.fly(10, "calm")
        self.assertEqual(samovar.energy, 0.0)
        self.assertEqual(samovar.position_km, 10.0)
        self.assert_fails_atomically(SamovarNoEnergy, samovar,
                                     samovar.fly, 0.1, "tailwind")
        # (d) не хватает энергии: нужно 21, есть 20; сценарий 2 из SPEC 4.1
        samovar = flying(energy=30)
        self.assert_fails_atomically(SamovarNoEnergy, samovar,
                                     samovar.fly, 10.5, "calm")
        samovar = flying(energy=20, max_speed_kmh=60)  # energy == 10
        self.assert_fails_atomically(SamovarNoEnergy, samovar,
                                     samovar.fly, 10, "calm")
        self.assertIs(samovar.is_flying, True)
        # (e) буря без достаточной энергии не рвёт баллон
        samovar = flying(energy=30)  # energy == 20, нужно 24
        self.assert_fails_atomically(SamovarNoEnergy, samovar,
                                     samovar.fly, 6, "storm")
        self.assertIs(samovar.envelope_intact, True)
        # (f) переполнение float трактуется как превышение запаса
        samovar = flying()
        self.assert_fails_atomically(SamovarNoEnergy, samovar,
                                     samovar.fly, 1e308, "storm")

    def test_TC_11_fly_invalid_arguments_and_priority(self):
        """TC-11: ValueError/TypeError аргументов fly и порядок проверок."""
        # ValueError: дистанция
        for bad in (0, -1, -0.1, NAN, INF, -INF):
            with self.subTest(distance=bad):
                samovar = flying()
                self.assert_fails_atomically(ValueError, samovar,
                                             samovar.fly, bad, "calm")
        # ValueError: погода (регистр и пробелы значимы)
        for bad in ("hurricane", "Calm", " calm", "calm ", ""):
            with self.subTest(weather=bad):
                samovar = flying()
                self.assert_fails_atomically(ValueError, samovar,
                                             samovar.fly, 10, bad)
        # TypeError: дистанция и погода
        for bad in ("10", None, True, False, [10]):
            with self.subTest(distance=bad):
                samovar = flying()
                self.assert_fails_atomically(TypeError, samovar,
                                             samovar.fly, bad, "calm")
        for bad in (None, 5, b"calm", True):
            with self.subTest(weather=bad):
                samovar = flying()
                self.assert_fails_atomically(TypeError, samovar,
                                             samovar.fly, 10, bad)
        # Порядок: все типы раньше всех значений
        samovar = flying()
        self.assert_fails_atomically(TypeError, samovar, samovar.fly, "10", "hurricane")
        self.assert_fails_atomically(TypeError, samovar, samovar.fly, 0, 5)
        # Порядок: аргументы раньше состояния (на земле)
        grounded = make()
        self.assert_fails_atomically(ValueError, grounded, grounded.fly, 0, "calm")
        self.assert_fails_atomically(TypeError, grounded, grounded.fly, "1", "calm")
        # Порядок: NotFlying раньше EnvelopeTorn
        grounded = make()
        grounded.damage_envelope()
        self.assert_fails_atomically(SamovarNotFlying, grounded,
                                     grounded.fly, 10, "calm")
        # Порядок: EnvelopeTorn раньше NoEnergy
        torn = flying()
        torn.damage_envelope()
        self.assert_fails_atomically(SamovarEnvelopeTorn, torn,
                                     torn.fly, 1000, "calm")


class LandTests(SamovarTestCase):
    def test_TC_12_land(self):
        """TC-12: посадка: сброс груза и признака полёта; ошибка на земле."""
        # (a) обычная посадка с грузом
        samovar = make()
        samovar.take_off(60)
        samovar.fly(10, "calm")  # energy == 70, position == 10
        result = samovar.land()
        self.assertIsNone(result)
        self.assertIs(samovar.is_flying, False)
        self.assertEqual(samovar.load_kg, 0.0)
        self.assertEqual(samovar.energy, 70.0)
        self.assertEqual(samovar.position_km, 10.0)
        # (b) аварийная посадка с разорванным баллоном допустима
        samovar = flying()
        samovar.fly(5, "storm")
        self.assertIs(samovar.envelope_intact, False)
        samovar.land()
        self.assertIs(samovar.is_flying, False)
        self.assertIs(samovar.envelope_intact, False)
        # (c) на земле посадка невозможна
        samovar = make()
        self.assert_fails_atomically(SamovarNotFlying, samovar, samovar.land)


class CanOvercomeTests(SamovarTestCase):
    def test_TC_13_can_overcome_tree_and_mountain(self):
        """TC-13: препятствия «tree» и «mountain» (граница энергии 30)."""
        # tree: только в полёте
        self.assertIs(make().can_overcome("tree"), False)
        self.assertIs(flying().can_overcome("tree"), True)
        # mountain: на земле — всегда False
        self.assertIs(make(energy=100).can_overcome("mountain"), False)
        # mountain: в полёте нужно energy > 30
        samovar = flying(energy=40)  # energy == 30
        self.assertIs(samovar.can_overcome("mountain"), False)
        samovar = flying(energy=40.5)  # energy == 30.5
        self.assertIs(samovar.can_overcome("mountain"), True)
        self.assertIs(flying().can_overcome("mountain"), True)  # energy == 90
        # Исправность баллона на эти правила не влияет
        samovar = flying()
        samovar.damage_envelope()
        self.assertIs(samovar.can_overcome("tree"), True)
        self.assertIs(samovar.can_overcome("mountain"), True)

    def test_TC_14_can_overcome_gorge_invalid_and_pure(self):
        """TC-14: «gorge» (граница 500 м³), ошибки аргумента, отсутствие побочных эффектов."""
        # gorge: по объёму баллона, независимо от полёта
        for volume, expected in ((400, True), (500, True), (500.5, False), (800, False)):
            with self.subTest(volume=volume):
                grounded = make(envelope_volume_m3=volume)
                self.assertIs(grounded.can_overcome("gorge"), expected)
                in_air = flying(envelope_volume_m3=volume)
                self.assertIs(in_air.can_overcome("gorge"), expected)
        # ValueError: неизвестное препятствие (регистр и пробелы значимы)
        for bad in ("cliff", "Tree", " tree", "tree ", ""):
            with self.subTest(obstacle=bad):
                samovar = flying()
                self.assert_fails_atomically(ValueError, samovar,
                                             samovar.can_overcome, bad)
        # TypeError: не строка
        for bad in (5, None, True, b"tree", ["tree"]):
            with self.subTest(obstacle=bad):
                samovar = flying()
                self.assert_fails_atomically(TypeError, samovar,
                                             samovar.can_overcome, bad)
        # Корректные вызовы состояние не меняют
        samovar = flying()
        before = snapshot(samovar)
        for obstacle in ("tree", "mountain", "gorge"):
            samovar.can_overcome(obstacle)
        self.assertEqual(snapshot(samovar), before)


class CalculateEnergyTests(SamovarTestCase):
    def test_TC_15_calculate_energy(self):
        """TC-15: расчёт затрат без изменения состояния и без проверок состояния."""
        # Arrange: на земле, энергия 0, баллон разорван — состояния не мешают расчёту
        samovar = make(energy=0)
        samovar.damage_envelope()
        before = snapshot(samovar)
        # Act / Assert: значения по погоде
        for weather, distance, expected in (
            ("calm", 10, 20.0),
            ("tailwind", 10, 10.0),
            ("headwind", 10, 30.0),
            ("storm", 10, 40.0),
            ("calm", 2.5, 5.0),
        ):
            with self.subTest(weather=weather, distance=distance):
                result = samovar.calculate_energy(distance, weather)
                self.assertIsInstance(result, float)
                self.assertAlmostEqual(result, expected, places=PLACES)
        self.assertEqual(snapshot(samovar), before)
        # Переполнение возвращает бесконечность
        self.assertEqual(samovar.calculate_energy(1e308, "storm"), INF)
        # Ошибки аргументов — те же, что у fly
        for bad in (0, -1, NAN, INF):
            with self.subTest(distance=bad):
                with self.assertRaises(ValueError):
                    samovar.calculate_energy(bad, "calm")
        for bad in ("hurricane", "Calm", ""):
            with self.subTest(weather=bad):
                with self.assertRaises(ValueError):
                    samovar.calculate_energy(10, bad)
        for bad in ("10", None, True):
            with self.subTest(distance=bad):
                with self.assertRaises(TypeError):
                    samovar.calculate_energy(bad, "calm")
        for bad in (None, 5):
            with self.subTest(weather=bad):
                with self.assertRaises(TypeError):
                    samovar.calculate_energy(10, bad)
        with self.assertRaises(TypeError):
            samovar.calculate_energy("10", "hurricane")  # типы раньше значений


class RefuelTests(SamovarTestCase):
    def test_TC_16_refuel(self):
        """TC-16: заправка, потолок 100, ошибки аргументов и состояния."""
        # (a) сценарий 4 из SPEC 4.1
        samovar = make(energy=20)
        result = samovar.refuel(50)
        self.assertIsNone(result)
        self.assertEqual(samovar.energy, 70.0)
        # (b) потолок 100, граница ровно 100 и дробное значение
        samovar = make(energy=50)
        samovar.refuel(1000)
        self.assertEqual(samovar.energy, 100.0)
        samovar = make(energy=20)
        samovar.refuel(80)
        self.assertEqual(samovar.energy, 100.0)
        samovar = make(energy=20)
        samovar.refuel(0.5)
        self.assertEqual(samovar.energy, 20.5)
        # (c) ValueError
        for bad in (0, -5, NAN, INF, -INF):
            with self.subTest(amount=bad):
                samovar = make(energy=20)
                self.assert_fails_atomically(ValueError, samovar, samovar.refuel, bad)
        # (d) TypeError
        for bad in ("5", True, False, None, [5]):
            with self.subTest(amount=bad):
                samovar = make(energy=20)
                self.assert_fails_atomically(TypeError, samovar, samovar.refuel, bad)
        # (e) в воздухе заправка запрещена
        samovar = flying()
        self.assert_fails_atomically(SamovarNotOnGround, samovar, samovar.refuel, 5)
        # (f) аргументы проверяются раньше состояния
        samovar = flying()
        self.assert_fails_atomically(ValueError, samovar, samovar.refuel, -1)
        self.assert_fails_atomically(TypeError, samovar, samovar.refuel, "5")


class EnvelopeTests(SamovarTestCase):
    def test_TC_17_damage_and_repair_envelope(self):
        """TC-17: повреждение и ремонт баллона (стоимость 15, ограничения)."""
        # (a) damage_envelope идемпотентен и работает в воздухе
        samovar = flying()
        self.assertIsNone(samovar.damage_envelope())
        self.assertIs(samovar.envelope_intact, False)
        samovar.damage_envelope()
        self.assertIs(samovar.envelope_intact, False)
        self.assertIs(samovar.is_flying, True)
        # (b) ремонт на земле: -15 энергии
        samovar = make(energy=50)
        samovar.damage_envelope()
        self.assertIsNone(samovar.repair_envelope())
        self.assertIs(samovar.envelope_intact, True)
        self.assertEqual(samovar.energy, 35.0)
        # (c) цел баллон — ничего не происходит
        samovar = make(energy=50)
        samovar.repair_envelope()
        self.assertEqual(samovar.energy, 50.0)
        self.assertIs(samovar.envelope_intact, True)
        # (d) граница энергии: ровно 15 — можно; 14.5 — нельзя
        samovar = make(energy=15)
        samovar.damage_envelope()
        samovar.repair_envelope()
        self.assertEqual(samovar.energy, 0.0)
        self.assertIs(samovar.envelope_intact, True)
        samovar = make(energy=14.5)
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarNoEnergy, samovar, samovar.repair_envelope)
        self.assertIs(samovar.envelope_intact, False)
        # (e) в воздухе ремонт запрещён (даже если баллон цел) и проверяется раньше энергии
        samovar = flying()
        self.assert_fails_atomically(SamovarNotOnGround, samovar, samovar.repair_envelope)
        samovar = flying(energy=15)  # energy == 5
        samovar.damage_envelope()
        self.assert_fails_atomically(SamovarNotOnGround, samovar, samovar.repair_envelope)


class StatusAndExceptionTests(SamovarTestCase):
    def test_TC_18_get_status(self):
        """TC-18: get_status: точные ключи, актуальные значения, независимый снимок."""
        # Arrange / Act: начальное состояние
        samovar = make()
        status = samovar.get_status()
        # Assert
        self.assertIsInstance(status, dict)
        self.assertEqual(
            set(status),
            {"name", "energy", "position_km", "is_flying", "envelope_intact", "load_kg"},
        )
        self.assertEqual(status, {
            "name": "Пар-Облако", "energy": 100.0, "position_km": 0.0,
            "is_flying": False, "envelope_intact": True, "load_kg": 0.0,
        })
        # Значения после действий
        samovar.take_off(60)
        samovar.fly(20, "tailwind")
        self.assertEqual(samovar.get_status(), {
            "name": "Пар-Облако", "energy": 70.0, "position_km": 20.0,
            "is_flying": True, "envelope_intact": True, "load_kg": 60.0,
        })
        # Снимок независим от объекта и от других снимков
        first = samovar.get_status()
        first["energy"] = 0.0
        first["name"] = "Подделка"
        second = samovar.get_status()
        self.assertIsNot(first, second)
        self.assertEqual(second["energy"], 70.0)
        self.assertEqual(samovar.energy, 70.0)
        self.assertEqual(samovar.name, "Пар-Облако")

    def test_TC_19_domain_exception_hierarchy(self):
        """TC-19: иерархия доменных исключений."""
        concrete = (SamovarNoEnergy, SamovarEnvelopeTorn, SamovarOverweight,
                    SamovarNotFlying, SamovarNotOnGround)
        self.assertTrue(issubclass(CrazyVehicleError, Exception))
        self.assertTrue(issubclass(SamovarError, CrazyVehicleError))
        for cls in (CrazyVehicleError, SamovarError) + concrete:
            with self.subTest(cls=cls.__name__):
                self.assertFalse(issubclass(cls, (ValueError, TypeError, RuntimeError)))
        for cls in concrete:
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, SamovarError))
        # Конкретные исключения не являются друг другу родителями
        for first in concrete:
            for second in concrete:
                if first is not second:
                    with self.subTest(first=first.__name__, second=second.__name__):
                        self.assertFalse(issubclass(first, second))


# --------------------------------------------------------------------------
# Сценарные тесты (Given-When-Then, через Pilot)
# --------------------------------------------------------------------------
class ScenarioTests(SamovarTestCase):
    def test_TC_20_tea_flight_over_the_pass(self):
        """TC-20: сценарий 5 «Чайный рейс над перевалом»."""
        # Given
        самовар = make(mass_kg=120, envelope_volume_m3=400, max_speed_kmh=40, energy=100)
        пилот = Pilot(самовар)
        self.assertIs(самовар.is_flying, False)
        self.assertIs(самовар.envelope_intact, True)

        # When: пилот берёт 60 кг груза и взлетает
        пилот.взлететь(60)
        # Then
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.load_kg, 60.0)
        self.assertEqual(самовар.energy, 90.0)

        # When: 20 км при попутном ветре
        время = пилот.лететь(20, "tailwind")
        # Then
        self.assertAlmostEqual(время, 20 / 60, places=PLACES)
        self.assertEqual(самовар.position_km, 20.0)
        self.assertEqual(самовар.energy, 70.0)

        # When: проверка препятствий
        # Then
        self.assertIs(пилот.проверить_препятствие("mountain"), True)
        self.assertIs(пилот.проверить_препятствие("tree"), True)
        self.assertIs(пилот.проверить_препятствие("gorge"), True)

        # When: 10 км при встречном ветре
        время = пилот.лететь(10, "headwind")
        # Then
        self.assertAlmostEqual(время, 0.5, places=PLACES)
        self.assertEqual(самовар.position_km, 30.0)
        self.assertEqual(самовар.energy, 40.0)
        self.assertIs(пилот.проверить_препятствие("mountain"), True)

        # When: 5 км в штиль
        время = пилот.лететь(5, "calm")
        # Then
        self.assertAlmostEqual(время, 0.125, places=PLACES)
        self.assertEqual(самовар.position_km, 35.0)
        self.assertEqual(самовар.energy, 30.0)
        self.assertIs(пилот.проверить_препятствие("mountain"), False)

        # When: посадка и заправка
        пилот.сесть()
        пилот.заправиться(50)
        # Then: итоговое состояние
        self.assertIs(самовар.is_flying, False)
        self.assertEqual(самовар.load_kg, 0.0)
        self.assertEqual(самовар.position_km, 35.0)
        self.assertEqual(самовар.energy, 80.0)
        self.assertIs(самовар.envelope_intact, True)

    def test_TC_21_storm_over_the_gorge(self):
        """TC-21: сценарий 6 «Буря над ущельем»."""
        # Given
        самовар = make(mass_kg=120, envelope_volume_m3=400, max_speed_kmh=40, energy=100)
        пилот = Pilot(самовар)

        # When: взлёт без груза и 10 км в штиль
        пилот.взлететь()
        время = пилот.лететь(10, "calm")
        # Then
        self.assertAlmostEqual(время, 0.25, places=PLACES)
        self.assertEqual(самовар.position_km, 10.0)
        self.assertEqual(самовар.energy, 70.0)

        # When: 5 км сквозь бурю
        время = пилот.лететь(5, "storm")
        # Then: баллон разорван, самовар ещё в воздухе
        self.assertAlmostEqual(время, 0.5, places=PLACES)
        self.assertEqual(самовар.position_km, 15.0)
        self.assertEqual(самовар.energy, 50.0)
        self.assertIs(самовар.envelope_intact, False)
        self.assertIs(самовар.is_flying, True)

        # When: пытается лететь дальше с разорванным баллоном
        # Then
        with self.assertRaises(SamovarEnvelopeTorn):
            пилот.лететь(1, "calm")
        self.assertEqual(самовар.position_km, 15.0)
        self.assertEqual(самовар.energy, 50.0)

        # When: аварийная посадка
        пилот.сесть()
        # Then
        self.assertIs(самовар.is_flying, False)
        self.assertIs(самовар.envelope_intact, False)

        # When: пытается снова взлететь без ремонта
        # Then
        with self.assertRaises(SamovarEnvelopeTorn):
            пилот.взлететь()
        self.assertIs(самовар.is_flying, False)
        self.assertEqual(самовар.energy, 50.0)

        # When: ремонтирует баллон
        пилот.чинить_баллон()
        # Then
        self.assertIs(самовар.envelope_intact, True)
        self.assertEqual(самовар.energy, 35.0)

        # When: взлетает снова
        пилот.взлететь()
        # Then: итоговое состояние
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.energy, 25.0)
        self.assertEqual(самовар.position_km, 15.0)
        self.assertIs(самовар.envelope_intact, True)
        self.assertEqual(самовар.load_kg, 0.0)

    def test_TC_22_overweight_and_empty_tank(self):
        """TC-22: сценарий 7 «Перегруз и пустой бак»."""
        # Given
        самовар = make(mass_kg=120, envelope_volume_m3=400, max_speed_kmh=40, energy=12)
        пилот = Pilot(самовар)

        # When: пытается взлететь с 90 кг (120 + 90 > 200)
        # Then
        with self.assertRaises(SamovarOverweight):
            пилот.взлететь(90)
        self.assertIs(самовар.is_flying, False)
        self.assertEqual(самовар.energy, 12.0)
        self.assertEqual(самовар.load_kg, 0.0)

        # When: взлетает с 80 кг (ровно предел)
        пилот.взлететь(80)
        # Then
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.load_kg, 80.0)
        self.assertEqual(самовар.energy, 2.0)

        # When: пытается пролететь 2 км в штиль (нужно 4)
        # Then
        with self.assertRaises(SamovarNoEnergy):
            пилот.лететь(2, "calm")
        self.assertEqual(самовар.position_km, 0.0)
        self.assertEqual(самовар.energy, 2.0)

        # When: летит 2 км с попутным ветром (нужно 2)
        время = пилот.лететь(2, "tailwind")
        # Then
        self.assertAlmostEqual(время, 2 / 60, places=PLACES)
        self.assertEqual(самовар.position_km, 2.0)
        self.assertEqual(самовар.energy, 0.0)

        # When: пытается лететь ещё 1 км
        # Then
        with self.assertRaises(SamovarNoEnergy):
            пилот.лететь(1, "tailwind")
        self.assertEqual(самовар.position_km, 2.0)
        self.assertEqual(самовар.energy, 0.0)

        # When: садится
        пилот.сесть()
        # Then
        self.assertIs(самовар.is_flying, False)
        self.assertEqual(самовар.load_kg, 0.0)

        # When: пытается взлететь с пустым баком
        # Then
        with self.assertRaises(SamovarNoEnergy):
            пилот.взлететь()
        self.assertIs(самовар.is_flying, False)
        self.assertEqual(самовар.energy, 0.0)

        # When: заправляется «с запасом» и взлетает
        пилот.заправиться(1000)
        self.assertEqual(самовар.energy, 100.0)
        пилот.взлететь()
        # Then: итоговое состояние
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.energy, 90.0)
        self.assertEqual(самовар.position_km, 2.0)
        self.assertEqual(самовар.load_kg, 0.0)

    def test_TC_23_big_envelope_liner(self):
        """TC-23: сценарий 8 «Облачный Лайнер: большой баллон»."""
        # Given
        самовар = FlyingSamovar("Облачный Лайнер", 300, 800, 30, 60)
        пилот = Pilot(самовар)
        self.assertEqual(самовар.lift_capacity_kg, 400.0)

        # When: проверка препятствий на земле
        # Then
        self.assertIs(пилот.проверить_препятствие("gorge"), False)
        self.assertIs(пилот.проверить_препятствие("tree"), False)
        self.assertIs(пилот.проверить_препятствие("mountain"), False)

        # When: взлёт с 100 кг (300 + 100 == 400, ровно предел)
        пилот.взлететь(100)
        # Then
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.load_kg, 100.0)
        self.assertEqual(самовар.energy, 50.0)
        self.assertIs(пилот.проверить_препятствие("tree"), True)
        self.assertIs(пилот.проверить_препятствие("mountain"), True)
        self.assertIs(пилот.проверить_препятствие("gorge"), False)

        # When: 10 км при встречном ветре
        время = пилот.лететь(10, "headwind")
        # Then
        self.assertAlmostEqual(время, 10 / 15, places=PLACES)
        self.assertEqual(самовар.position_km, 10.0)
        self.assertEqual(самовар.energy, 20.0)
        self.assertIs(пилот.проверить_препятствие("mountain"), False)

        # When: 7 км в штиль
        время = пилот.лететь(7, "calm")
        # Then
        self.assertAlmostEqual(время, 7 / 30, places=PLACES)
        self.assertEqual(самовар.position_km, 17.0)
        self.assertEqual(самовар.energy, 6.0)

        # When: ещё 4 км в штиль (нужно 8)
        # Then
        with self.assertRaises(SamovarNoEnergy):
            пилот.лететь(4, "calm")
        # Then: итоговое состояние
        self.assertEqual(самовар.position_km, 17.0)
        self.assertEqual(самовар.energy, 6.0)
        self.assertIs(самовар.is_flying, True)
        self.assertEqual(самовар.load_kg, 100.0)
        self.assertIs(самовар.envelope_intact, True)


if __name__ == "__main__":
    unittest.main()
