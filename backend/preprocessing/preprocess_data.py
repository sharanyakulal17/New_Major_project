import pandas as pd
data = pd.read_csv("monitoring/datasets/system_metrics.csv")                        #load dataset

print(data.head())                                                                  #show first five rows

print("\nDataset Shape: - preprocess_data.py:6")                                    #Number of rows and columns
print(data.shape)

print("\nColumn Names: - preprocess_data.py:9")                                      #Column names
print(data.columns)

print("\nData Types: - preprocess_data.py:12")                                       #Data types
print(data.dtypes)

print("\nMissing Values: - preprocess_data.py:15")                                   #Missing values
print(data.isnull().sum())

print("\nDuplicate Rows: - preprocess_data.py:18")                                   #Check duplicate rows
print(data.duplicated().sum())

#Convert text columns into numbers
data["Status"] = data["Status"].map({                                                #data["status"] --> selects status column
    "Normal" : 0,                                                                     #map --> replace the value like normal -> 1 , anomaly -> 0
    "Anomaly" : 1
})

data["Health Check"] = data["Health Check"].map({
     "Healthy" : 0,
     "Unhealthy" : 1
})

data["Service Status"] = data["Service Status"].map({
    "Running" : 0,
    "Degraded" : 1
})

print("/nEncoded Dataset: - preprocess_data.py:37")
print(data.head())