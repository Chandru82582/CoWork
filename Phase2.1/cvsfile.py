import csv 

CSV_FILE_PATH = "telecom_churn.csv"

with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as csvfile:
            # Assuming the CSV has a header row
            reader = csv.DictReader(csvfile)

            for row in reader:
                print(row)
                break


# print(reader)