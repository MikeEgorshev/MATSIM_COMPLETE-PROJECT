# New PC Setup Requirements (Shamalgan MATSim Project)

This file describes the exact requirements to run this project on a new PC.

## 1) Required Software

- Git (latest stable)
- Git LFS (required for large run/output files in this repository)
- Java JDK 17 (required by MATSim 2025.x project setup)
- Python 3.10+ (for helper scripts and plots)
- PowerShell (Windows default)
- IntelliJ IDEA (optional but recommended)

## 2) Verify Install

Run in terminal:

git --version
git lfs version
java -version
python --version

Expected:
- Java reports version 17.x
- git-lfs command is available

## 3) Clone Project

git clone https://github.com/MikeEgorshev/MATSIM_COMPLETE-PROJECT.git
cd MATSIM_COMPLETE-PROJECT

## 4) Pull LFS Files

git lfs install
git lfs pull

## 5) Python Dependency

python -m pip install --upgrade pip
python -m pip install matplotlib

## 6) Build and Sanity Check

.\mvnw.cmd -q -DskipTests compile

## 7) Typical Run Commands

Run PT-enabled scenario with SimWrapper:

.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.RunShamalgan" "-Dexec.args=scenarios/shamalgan/config-pt.xml --simwrapper"

Rebuild network with current poor-road profile:

.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganNetwork" "-Dexec.args=original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643 poor"

Rebuild PT supply from assumptions:

.\mvnw.cmd -q exec:java "-Dexec.mainClass=org.matsim.project.PrepareShamalganTransitFromAssumptions" "-Dexec.args=scenarios/shamalgan/network.xml analysis-artifacts/pt-data/osm_bus_stops.csv scenarios/shamalgan/network-with-pt.xml scenarios/shamalgan/transitSchedule.xml scenarios/shamalgan/transitVehicles.xml 30 60 360 06:00:00 23:00:00"

## 8) Notes

- This repo may include heavy output files; cloning can take time.
- If LFS files appear as small pointer text files, run `git lfs pull` again.
