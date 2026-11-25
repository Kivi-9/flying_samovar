# Демо «Буря над ущельем»

Показ разработчика по сценарию 6 из ТЗ и тесту TC-21. Самовар массой 120 кг с баллоном 400 м³ начинает на земле со 100 единицами энергии. После бури пилот проверяет, может ли аппарат продолжить полёт, затем садится, чинит баллон и снова взлетает.

## Повторить сценарий

В корне репозитория запустите `python` и выполните:

```python
from flying_samovar import FlyingSamovar, SamovarEnvelopeTorn

samovar = FlyingSamovar("Пар-Облако", 120, 400, 40)
samovar.take_off()
print("Штиль, ч", samovar.fly(10, "calm"))
print("Буря, ч", samovar.fly(5, "storm"))
print("После бури", samovar.get_status())

try:
    samovar.fly(1, "calm")
except SamovarEnvelopeTorn as error:
    print(type(error).__name__)

samovar.land()
samovar.repair_envelope()
samovar.take_off()
print("После ремонта и взлёта", samovar.get_status())
```

| Шаг | Что показать |
|---|---|
| После штиля | Время 0.25 ч, пройдено 10 км, остаток 70 |
| После бури | Время 0.5 ч, пройдено 15 км, остаток 50, баллон разорван, аппарат в воздухе |
| Попытка продолжить полёт | `SamovarEnvelopeTorn`, позиция и энергия прежние |
| После посадки, ремонта и нового взлёта | Аппарат в воздухе, баллон цел, позиция 15 км, остаток 25 |

## Прогон на защите

```sh
python -B -m unittest tests.test_flying_samovar.ScenarioTests.test_TC_21_storm_over_the_gorge -v
python -B -m unittest discover -s tests -t . -v
```

TC-21 дополнительно проверяет, что после посадки повторный взлёт с повреждённым баллоном поднимает `SamovarEnvelopeTorn`.
