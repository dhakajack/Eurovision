from openpyxl import Workbook
import sqlite3


def flatten(t):
    return [item for sublist in t for item in sublist]


trial_terms = ("status", "db_date", "title", "nct", "placebo", "condition",
               "meddra_version", "meddra_level", "meddra_classification",
               "meddra_term", "meddra_soc", "rare", "fih", "bioequivalence",
               "phase1", "phase2", "phase3", "phase4", "diagnosis", "prophylaxis",
               "therapy", "safety", "efficacy", "pk", "pd", "randomised",
               "open_design", "single_blind", "double_blind", "crossover",
               "age_in_utero", "age_preterm", "age_newborn", "age_under2",
               "age_2to11", "age12to17", "age18to64", "age_65plus", "female",
               "male", "network", "eot_date")

drug_terms = ("trade", "product", "code", "inn", "cas", "sponsor_code", "ev_substance",
              "alt_names")

sponsor_terms = ("name", "org", "contact", "email")

drug_list = []

trial_selected = "2004-000028-34"
database = "BIG2"

wb = Workbook()
ws = wb.active
ws.title = "Test Record"

trial_term_string = ", ".join(trial_terms)
drug_term_string = ", ".join(drug_terms)
sponsor_term_string = "name"
location_term_string = "location"

headers = list(trial_terms)
headers.append("drug")
headers.append("sponsor")
headers.append("location")
ws.append(headers)

db = sqlite3.connect(database)
cursor = db.cursor()

drugs_list = []

cursor.execute("SELECT {} FROM  trial WHERE eudract = \"{}\"".format(trial_term_string, trial_selected))
extract = cursor.fetchone()
trial_data = list(extract)
cursor.execute("SELECT {} FROM drug WHERE eudract = \"{}\"".format(drug_term_string, trial_selected))
rows = cursor.fetchall()
for drug_data in rows:
    if drug_data[3]:
        drug_name_source = 3
    elif drug_data[1]:
        drug_name_source = 0
    elif drug_data[0]:
        drug_name_source = 2
    elif drug_data[2]:
        drug_name_source = 4
    elif drug_data[4]:
        drug_name_source = 6
    elif drug_data[6]:
        drug_name_source = 1
    elif drug_data[7]:
        drug_name_source = 7
    else:
        drug_name_source = 5
    drug_list.append(drug_terms[drug_name_source] + ":" + drug_data[drug_name_source])
drug_entry = "; ".join(drug_list)
cursor.execute("SELECT {} FROM location WHERE eudract = \"{}\"".format(location_term_string, trial_selected))
rows = cursor.fetchall()
location_entry = ", ".join(flatten(rows))
cursor.execute("SELECT {} FROM sponsor WHERE eudract = \"{}\"".format(sponsor_term_string, trial_selected))
sponsor_entry = cursor.fetchone()[0]
trial_data.append(drug_entry)
trial_data.append(location_entry)
trial_data.append(sponsor_entry)

ws.append(trial_data)
wb.save(database + ".xlsx")
db.close()
