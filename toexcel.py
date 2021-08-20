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

trial_term_string = ", ".join(trial_terms)
drug_term_string = ", ".join(drug_terms)
sponsor_term_string = "name"
location_term_string = "location"

database = "big6"

drug_list = {}

trial_selected = "2004-000028-34"

result_set = {"trial": set(),
              "drug": set(),
              "sponsor": set(),
              "location": set()
              }

final_set = {}


db = sqlite3.connect(database)
cursor = db.cursor()


def search_a_table(table:str, the_cursor:cursor) -> bool:
    search_term = input('{} Data: Enter a WHERE clause > '.format(table.title()))
    if search_term == "":
        if table == "trial":            # trial is guaranteed to have an entry for all trials
            search_term = "1=1"         # the other tables only list a trial if there is data
        else:                           # for that trial
            return False
    the_cursor.execute("SELECT eudract FROM {} WHERE {}".format(table, search_term))
    hits = flatten(the_cursor.fetchall())
    print("The number of hits is: {}".format(len(hits)))
    result_set[table] = set(hits)
    return True

while True:

    # Input search parameters
    search_a_table("trial", cursor)
    drug_flag = search_a_table("drug", cursor)
    location_flag = search_a_table("location", cursor)
    sponsor_flag = search_a_table("sponsor", cursor)
    final_set = result_set["trial"]
    if drug_flag:
        final_set = final_set & result_set["drug"]
    if location_flag:
        final_set = final_set & result_set["location"]
    if sponsor_flag:
        final_set = final_set & result_set["sponsor"]
    print("Final data set includes {} trials".format(len(final_set)))



    break




    cursor.execute("SELECT {} FROM trial WHERE eudract = \"{}\"".format(trial_term_string, trial_selected))
    extract = cursor.fetchone()
    trial_data = list(extract)
    cursor.execute("SELECT {} FROM drug WHERE eudract = \"{}\"".format(drug_term_string, trial_selected))
    rows = cursor.fetchall()
    for drug_data in rows:
        if drug_data[3]: # prefer INN
            drug_name_source = 3
        elif drug_data[1]: # product name
            drug_name_source = 1
        elif drug_data[0]: # trade name
            drug_name_source = 0
        elif drug_data[2]: # product code
            drug_name_source = 2
        elif drug_data[4]: # CAS number
            drug_name_source = 4
        elif drug_data[6]: # EV substance code
            drug_name_source = 6
        elif drug_data[7]: # alternative names
            drug_name_source = 7
        else:
            drug_name_source = 5 # sponsor code
        drug_list.append(drug_terms[drug_name_source] + ":" + drug_data[drug_name_source])
    drug_entry = "; ".join(drug_list)
    cursor.execute("SELECT {} FROM location WHERE eudract = \"{}\"".format(location_term_string, trial_selected))
    rows = cursor.fetchall()
    location_entry = ", ".join(flatten(rows))
    cursor.execute("SELECT {} FROM sponsor WHERE eudract = \"{}\"".format(sponsor_term_string, trial_selected))
    sponsor_entry = cursor.fetchone()[0] # sponsor name
    trial_data.append(drug_entry)
    trial_data.append(location_entry)
    trial_data.append(sponsor_entry)

    wb = Workbook()
    ws = wb.active
    ws.title = "Test Record"
    headers = list(trial_terms)
    headers.append("drug")
    headers.append("sponsor")
    headers.append("location")
    ws.append(headers)
    ws.append(trial_data)
    wb.save(database + ".xlsx")



db.close()
