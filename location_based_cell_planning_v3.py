import pandas as pd
from pygeodesy.ellipsoidalExact import LatLon, perimeterOf
import time as timer
from tqdm import tqdm

'''
Created by Jan Kyle Lewis T. Nolasco
'''

def calculate_distance(lon1, lat1, lon2, lat2):
    points=LatLon(lat1, lon1), LatLon(lat2, lon2)

    return perimeterOf(points)/1000

def prefilter_neighbors_custom(neighbor_db, site_lon, site_lat, search_radius):
    '''
    #IMPORTANT
    lat is N, lon is E
    '''
    site_loc = LatLon(site_lat, site_lon)

    d = (search_radius * 1000) + 500

    lat_max = site_loc.destination(d, 0).latlon2(ndigits=6)[0]
    lon_max = site_loc.destination(d, 90).latlon2(ndigits=6)[1]
    lat_min = site_loc.destination(d, 180).latlon2(ndigits=6)[0]
    lon_min = site_loc.destination(d, 270).latlon2(ndigits=6)[1]

    if lat_min < site_lat < lat_max and lon_min < site_lon < lon_max:
        # drop all lon, lat not in search area
        neighbor_db = neighbor_db.drop(neighbor_db.loc[neighbor_db['Latitude'] > lat_max].index)
        neighbor_db = neighbor_db.drop(neighbor_db.loc[neighbor_db['Longitude'] > lon_max].index)
        neighbor_db = neighbor_db.drop(neighbor_db.loc[neighbor_db['Latitude'] < lat_min].index)
        neighbor_db = neighbor_db.drop(neighbor_db.loc[neighbor_db['Longitude'] < lon_min].index)

        return neighbor_db
    else:
        print("Prefilter algorithm failed, using backup algorithm.")
        return neighbor_db

def find_neighbors_custom(neighbor_db, site_lon, site_lat, prefilter_col, prefilter_col_value, search_radius):
    neighbor_db['Distance from site (km)'] = ""
    neighbor_db = neighbor_db.astype({'Site Code': 'string'})
    neighbor_db.drop(neighbor_db.loc[neighbor_db[prefilter_col] != prefilter_col_value].index, inplace=True)

    #prefilter neighbors
    neighbor_db=prefilter_neighbors_custom(neighbor_db, site_lon, site_lat, search_radius)

    for ind in neighbor_db.index:
        lon2=neighbor_db.loc[ind]['Longitude']
        lat2 = neighbor_db.loc[ind]['Latitude']
        distance=calculate_distance(site_lon, site_lat, lon2, lat2)
        neighbor_db.loc[ind, 'Distance from site (km)'] = distance

    neighbor_db.drop(neighbor_db.loc[neighbor_db['Distance from site (km)'] > search_radius].index, inplace=True)
    neighbor_db.sort_values(by=['Distance from site (km)'], inplace=True)
    neighbor_db.reset_index(drop=True, inplace=True)
    return neighbor_db

def assign_loc_param(loc_cell_param, neighbor_db, site_lon, site_lat, prefilter_col, prefilter_col_value, site, init_search_radius, filter, threshold):
    filtered_neighbors=find_neighbors_custom(neighbor_db, site_lon, site_lat, prefilter_col, prefilter_col_value, init_search_radius)

    #extend search radius until n_filter neighbors are found
    search_radius=init_search_radius+5
    while len(filtered_neighbors.index)<filter:
        #print(f"Site: {site}, extending search radius to {search_radius} km")
        filtered_neighbors = find_neighbors_custom(neighbor_db, site_lon, site_lat, prefilter_col, prefilter_col_value, search_radius)
        search_radius=search_radius+5

    filtered_neighbors=filtered_neighbors.head(filter)

    loc_cell_param_count=pd.DataFrame(columns=[loc_cell_param, "Points"])
    loc_cell_param_count[loc_cell_param]=filtered_neighbors[loc_cell_param]
    loc_cell_param_count.drop_duplicates(subset=[loc_cell_param], inplace=True)
    loc_cell_param_count.set_index(loc_cell_param, inplace=True)
    loc_cell_param_count["Points"] = 0

    for index in filtered_neighbors.index:
        curr_loc_cell_param=filtered_neighbors.loc[index, loc_cell_param]
        loc_cell_param_count.loc[curr_loc_cell_param, "Points"]=loc_cell_param_count.loc[curr_loc_cell_param, "Points"]+filter
        filter=filter-1

    loc_cell_param_count.sort_values(by="Points", ascending=False, inplace=True)
    loc_cell_param_count.reset_index(inplace=True)
    loc_cell_param_planned=loc_cell_param_count.loc[0, loc_cell_param]
    total_points=loc_cell_param_count["Points"].sum()
    loc_cell_param_points=round((loc_cell_param_count.loc[0, "Points"]/total_points)*100, 2)

    if loc_cell_param_points > threshold:
        border_flag = False
    else:
        border_flag = True
        #print("Border site found: ", site)
        #print(loc_cell_param_count)

    return loc_cell_param_planned, loc_cell_param_count.loc[0, "Points"], total_points, loc_cell_param_points, border_flag

def loc_param_planning_experiment(loc_cell_param, neighbor_db, rf_db, prefilter_col, init_search_radius, filter, threshold):
    rf_db.reset_index(inplace=True, drop=True)

    loc_cell_param_planned_col=loc_cell_param+" (Planned)"
    loc_cell_param_points_col=loc_cell_param+" Points"

    #rf_db["Search Radius"]=""
    rf_db[loc_cell_param_planned_col]=""
    rf_db[loc_cell_param_points_col]=""
    rf_db["Total"]=""
    rf_db["Score"]=""
    rf_db["Match?"]=False
    rf_db["Border Flag"]=""

    for index in tqdm(rf_db.index):
        site_lon=rf_db.loc[index, "Longitude"]
        site_lat=rf_db.loc[index, "Latitude"]
        prefilter_col_value=rf_db.loc[index, prefilter_col]
        site=rf_db.loc[index, "Site Code"]

        curr_loc_cell_param, point, total_points, score, border_flag=assign_loc_param(loc_cell_param, neighbor_db.copy(deep=True), site_lon,
                                                         site_lat, prefilter_col, prefilter_col_value, site, init_search_radius, filter, threshold)


        rf_db.loc[index, loc_cell_param_planned_col]=curr_loc_cell_param
        rf_db.loc[index, loc_cell_param_points_col]=point
        rf_db.loc[index, "Total"]=total_points
        rf_db.loc[index, "Score"]=score
        if rf_db.loc[index, loc_cell_param]==curr_loc_cell_param:
            rf_db.loc[index, "Match?"]=True
        rf_db.loc[index, "Border Flag"]=border_flag

    return rf_db

def main():
    print("")

if __name__ == "__main__":
    start = timer.time()
    main()
    end = timer.time()
    total_time = (end - start) / 60
    print(f"Elapsed Time: {total_time} mins", )
