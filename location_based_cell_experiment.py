import pandas as pd
from location_based_cell_planning_v3 import loc_param_planning_experiment
from statistics import mean, stdev
import time as timer
import os

'''
Created by Jan Kyle Lewis T. Nolasco
'''

def create_experiment_db(raw_db, sample_percent):
    test_samples=int(len(raw_db.index)*sample_percent)
    test_db=raw_db.sample(n=test_samples)
    #test_db.to_csv("test_db.csv")

    test_idx=test_db.index
    src_db=raw_db.drop(index=test_idx)

    return test_db, src_db

def loc_experiment(rat, loc_cell_param, prefilter_col, sample_percent, exp_param_db):
    # generate output folder
    output_folder = os.path.join(os.getcwd(), "experiment_result")
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    #import site database
    dtype={
        "Site Code": str
    }

    use_cols=["Site Code", "Longitude", "Latitude", prefilter_col, loc_cell_param]

    raw_db=pd.read_excel(f"RF_database.xlsx", dtype=dtype, usecols=use_cols, sheet_name=rat)
    raw_db=raw_db.drop_duplicates(subset=["Site Code"])
    raw_db.reset_index(drop=True, inplace=True)

    #sample site database and split database into test and source databases
    test_db, src_db=create_experiment_db(raw_db, sample_percent)
    #test_db.to_csv(f"{rat}_{loc_cell_param}.csv", index=False)

    exp_param_db["Accuracy"]=""

    for index in exp_param_db.index:
        filter=exp_param_db.loc[index, "Filter"]
        threshold=exp_param_db.loc[index, "Threshold"]
        print(f"Current Filter/Threshold: {filter}/{threshold}")

        planned_loc_param=loc_param_planning_experiment(loc_cell_param, src_db.copy(deep=True), test_db.copy(deep=True),
                                                        prefilter_col, 5, filter, threshold)

        #only check the accuracy of sites that have border_flag=False
        temp=planned_loc_param.drop(planned_loc_param.loc[planned_loc_param['Border Flag'] == True].index)
        total = len(temp.index)
        correct = temp["Match?"].value_counts()[True]
        accuracy = (correct / total) * 100
        exp_param_db.loc[index, "Accuracy"]=accuracy

        #export test db's for checking
        output_file_name = f"{rat}_{loc_cell_param}_filter_{filter}_threshold_{threshold}.xlsx"
        output_path = os.path.join(output_folder, output_file_name)
        planned_loc_param.to_excel(output_path, index=False)


    exp_param_db.to_excel(f"{rat}_{loc_cell_param}_experiment_accuracy_summary.xlsx", index=False)

    return exp_param_db

def multi_loc_experiment(trials, rat, loc_cell_param, prefilter_col, sample_percent, exp_param_db):
    #save accuracy columns to calculate average and std. dev
    accuracy_col_list=[]

    #repeat experiment based on number of set trials
    for i in range(trials):
        print(f"Current Trial: {i+1}/{trials}")

        exp_result = loc_experiment(rat, loc_cell_param, prefilter_col, sample_percent, exp_param_db.copy(deep=True))

        accuracy_column="Accuracy Trial "+str(i+1)
        accuracy_col_list.append(accuracy_column)
        exp_param_db[accuracy_column]=exp_result["Accuracy"]

    exp_param_db["AVG Accuracy"]=""
    exp_param_db["STDEV Accuracy"]=""
    #calculate average and std. dev
    for index in exp_param_db.index:
        accuracy=[]
        for accuracy_col in accuracy_col_list:
            accuracy.append(exp_param_db.loc[index, accuracy_col])

        exp_param_db.loc[index, "AVG Accuracy"]=mean(accuracy)
        exp_param_db.loc[index, "STDEV Accuracy"]=stdev(accuracy)

    exp_param_db.sort_values(by="AVG Accuracy", ascending=False, inplace=True)

    return exp_param_db

def main():
    rat="LTE"
    loc_cell_param="TAC"
    prefilter_col="Region"
    sample_percent = 0.05
    trials=2
    exp_param_db=pd.read_csv("experiment_parameters.csv")

    exp_result=multi_loc_experiment(trials, rat, loc_cell_param, prefilter_col, sample_percent,
                                    exp_param_db.copy(deep=True))
    print(exp_result)
    exp_result.to_csv("experiment_result.csv", index=False)

if __name__ == "__main__":
    start = timer.time()
    main()
    end = timer.time()
    total_time = (end - start) / 60
    print(f"Elapsed Time: {total_time} mins", )