import pandas as pd

# Liste officielle ECCC des stations
stations_url = "https://collaboration.cmc.ec.gc.ca/cmc/climate/Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv"

stations = pd.read_csv(stations_url, encoding='latin1')

# Chercher Montréal
montreal_stations = stations[stations['Name'].str.contains('MONTREAL', case=False, na=False)]
print(montreal_stations[['Name', 'Climate ID', 'Station ID', 'Province', 
                         'First Year', 'Last Year']])