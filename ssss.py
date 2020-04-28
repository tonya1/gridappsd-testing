
import json
import pandas as pd
from deepdiff import DeepDiff

file1 = "/tmp/output/power3.json"
file2 = "./simulation_baseline_files/9500-query3.json"
a = []


with open("./query.json", 'r') as f:
    alka = json.load(f)
    print(alka)
    print(alka["queryFilter"]["simulation_id"])

def assert_files_are_equal(file1, file2):
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:

            dict1 = json.load(f1)
            print(dict1)
            dict2 = json.load(f2)

            print(dict2)
            if len(dict1) != len(dict2):
                return False
            for y in dict1:
                m = dict1[y]
                for k in dict2:
                    n = dict2[k]
                    if "objectTypes" in m.keys():
                        if m.get("objectTypes") == n.get("objectTypes"):
                            print("both objects same")
                            return False
            return True


assert_files_are_equal(file1, file2)


