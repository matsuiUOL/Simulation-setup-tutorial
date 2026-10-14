import pandas as pd
df = pd.read_csv("mh_riv_v2.csv")
df[["mh_id","riv_no"]].to_csv("mh_to_riv_V2.dat", sep=" ", header=False, index=False)
