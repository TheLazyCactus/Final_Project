import pandas as pd

user_data = pd.read_excel(r"D:\Documents\GitHub\Final_Project\user_input_sample.xlsx")
reference = pd.read_excel(r"D:\Documents\GitHub\Final_Project\reference_sample.xlsx")
master = pd.read_csv(r"D:\Documents\GitHub\Final_Project\master_data_sample.csv")


#compare product column between user_data and reference then put according data in master
columns_to_merge = [col for col in reference.columns if col != 'product']

# Merge using the common column
df = user_data.merge(reference, on='product', how='left')

#calculate the specific weight and footprint
df["weight"] = df["price"]/ df["€/kg"] 
df['total_kg_co2'] = df['footprint_kg'] * df["weight"] /1000
df['total_kg_co2_farming'] = df['farming_kg'] * df["weight"] /1000
df['total_kg_co2_processing'] = df['processing_kg'] * df["weight"] /1000
df['total_kg_co2_packaging'] = df['packaging_kg'] * df["weight"] /1000
df['total_kg_co2_transport'] = df['transport_kg'] * df["weight"] /1000
df['total_kg_co2_retail'] = df['retail_kg'] * df["weight"] /1000
df['total_kg_co2_consumption'] = df['consumption_kg'] * df["weight"] /1000

#select only the relevant columns in the ,aster file
columns_to_keep = ["date","product_family","product", "weight","price","link",	"total_kg_co2",	"total_kg_co2_farming",	"total_kg_co2_processing",	"total_kg_co2_packaging",	"total_kg_co2_transport",	"total_kg_co2_retail",	"total_kg_co2_consumption"] 

filtered_df = df[columns_to_keep]
updated_df = pd.concat([master, filtered_df]).drop_duplicates(subset=['date', 'product'], keep='first')

updated_df.to_csv(r"D:\Documents\GitHub\Final_Project\master_data_sample.csv", index=False)