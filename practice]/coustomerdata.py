import kagglehub
import shutil
# Download latest version
path = kagglehub.dataset_download("suraj520/telecom-churn-dataset")
csv_path = path+"\\telecom_churn.csv"
print(csv_path)

shutil.copy(csv_path, "telecom_churn.csv")

print("Path to dataset files:", path)