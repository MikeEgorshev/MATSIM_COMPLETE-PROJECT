# Установка на новом ПК (проект MATSim Шамалган)

Требования для запуска проекта на чистой машине.

## 1) Необходимое ПО

- Git (последняя стабильная версия)
- Git LFS (для больших выходных файлов)
- Java JDK 17 (для MATSim 2025.x)
- Python 3.10+ (для скриптов и графиков)
- PowerShell (по умолчанию в Windows)
- IntelliJ IDEA (по желанию)

## 2) Проверка установки

В терминале:

```text
git --version
git lfs version
java -version
python --version
```

Ожидается: Java 17.x, доступна команда git-lfs.

## 3) Клонирование

```text
git clone https://github.com/MikeEgorshev/MATSIM_COMPLETE-PROJECT.git
cd MATSIM_COMPLETE-PROJECT
```

## 4) Подтянуть LFS-файлы

```text
git lfs install
git lfs pull
```

## 5) Зависимости Python

```text
python -m pip install --upgrade pip
python -m pip install matplotlib
```

## 6) Сборка и проверка

```powershell
.\mvnw.cmd -q -DskipTests compile
```

## 7) Типовые команды запуска

Запуск с ОТ и SimWrapper:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config.xml --simwrapper"
```

Пересборка сети (профиль «плохих» дорог):

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643 poor"
```

Пересборка ОТ по допущениям:

```powershell
.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"
```

## 8) Замечания

- Клонирование может занять время из-за больших выходных файлов.
- Если LFS-файлы выглядят как маленькие pointer-файлы, выполнить снова `git lfs pull`.
