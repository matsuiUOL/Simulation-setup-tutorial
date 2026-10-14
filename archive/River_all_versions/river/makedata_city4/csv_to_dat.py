import pandas as pd
df = pd.read_csv("mh_riv.csv")
df[["mh_id","riv_no"]].to_csv("mh_to_riv.dat", sep=" ", header=False, index=False)
