from openpyxl import Workbook
import sqlite3


def flatten(t):
    """
    Returns a flat list.
    :param t: An arbitrarily nested sequence.
    :return: List.
    """
    return [item for sublist in t for item in sublist]


def search_a_table(table: str, the_cursor: sqlite3.Cursor) -> bool:
    """
    Asks user for search parameters for a given table. Puts eudract number
    for any matching trial into the respective result set.
    :param table: A database table.
    :param the_cursor: A database cursor.
    :return: Returns true unless no parameter is entered for a table other than "trial".
    """

    search_term = input('{} Data: Enter a WHERE clause > '.format(table.title()))
    if search_term == "":
        if table == "trial":            # trial is guaranteed to have an entry for all trials
            search_term = "1=1"         # the other tables only list a trial if there is data
        else:                           # for that trial
            return False
    the_cursor.execute("SELECT eudract_id FROM {} WHERE {}".format(table, search_term))
    hits = flatten(the_cursor.fetchall())
    print("The number of hits is: {}".format(len(hits)))
    result_set[table] = set(hits)
    return True


database = "20210826-1644.sqlite3"

result_set = {"trial": set(),
              "imp": set(),
              "sponsor": set(),
              "location": set()
              }

final_set = {}
imp_list = []
display_trial = ["eudract_id",
                 "official_title",
                 "condition",
                 "enrollment",
                 "overall_status",
                 "phase1",
                 "phase2",
                 "phase3",
                 "phase4",
                 "meddra_version",
                 "meddra_level",
                 "meddra_classification",
                 "meddra_term",
                 "meddra_soc",
                 "nct_id",
                 "who_utrn_id",
                 "isrctn_id",
                 "sponsor_id",
                 "study_first_submitted_date",
                 "completion_date",
                 "therapy",
                 "diagnosis",
                 "prophylaxis",
                 "safety",
                 "efficacy",
                 "pk",
                 "pd",
                 "randomised",
                 "placebo",
                 "open_design",
                 "single_blind",
                 "double_blind",
                 "crossover",
                 "rare",
                 "fih",
                 "bioequivalence",
                 "age_in_utero",
                 "age_preterm",
                 "age_newborn",
                 "age_under2",
                 "age_2to11",
                 "age12to17",
                 "age18to64",
                 "age_65plus",
                 "female",
                 "male",
                 "network"]  # TO CONSIDER: make this a customizable list
trial_terms_string = ", ".join(display_trial)
imp_terms = ("trade", "product", "code")
imp_term_string = ", ".join(imp_terms)

db = sqlite3.connect(database)
cursor = db.cursor()

while True:

    # Input search parameters
    search_a_table("trial", cursor)
    imp_flag = search_a_table("imp", cursor)
    location_flag = search_a_table("location", cursor)
    sponsor_flag = search_a_table("sponsor", cursor)

    # Intersect result sets from search on each table to yield a final set
    final_set = result_set["trial"]
    if imp_flag:                            # only bother intersecting with imp table result if a search parameter
        final_set &= result_set["imp"]      # was provided; i.e., do not narrow the search if not imp parameter.
    if location_flag:
        final_set &= result_set["location"]  # same for location and sponsor.
    if sponsor_flag:
        final_set &= result_set["sponsor"]

    # Summarize result of search and ask user whether it is worthwhile to dump result to an excel spreadsheet
    print("Final data set includes {} trials".format(len(final_set)))
    output_file = input('Enter file name for output or "A" to abort >')
    if output_file.casefold() == "a":
        print("Aborted.")
        continue

    # Create a new excel spreadsheet with the result set
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Test Record"  # Later, make this more interesting. Consider adding search terms to another tab.
        headers = display_trial[::]
        headers.extend(("imp", "location", "sponsor"))
        ws.append(headers)

        for trial_selected in sorted(final_set):
            cursor.execute("SELECT {} FROM trial WHERE eudract_id = \"{}\"".
                           format(trial_terms_string, trial_selected))
            extract = cursor.fetchone()
            trial_data = list(extract)
            cursor.execute("SELECT {} FROM imp WHERE eudract_id = \"{}\""
                           .format(imp_term_string, trial_selected))
            rows = cursor.fetchall()
            imp_list.clear()
            for imp_data in rows:
                if imp_data[1]:            # prefer product name
                    imp_name_source = 1
                elif imp_data[0]:          # product trade name
                    imp_name_source = 0
                else:
                    imp_name_source = 2    # product code
                imp_list.append(imp_terms[imp_name_source] + ":" + imp_data[imp_name_source])
            imp_entry = "; ".join(imp_list)
            cursor.execute("SELECT location FROM location WHERE eudract_id = \"{}\""
                           .format(trial_selected))
            rows = cursor.fetchall()
            location_entry = ", ".join(flatten(rows))
            cursor.execute("SELECT name FROM sponsor WHERE eudract_id = \"{}\""
                           .format(trial_selected))
            sponsor_entry = cursor.fetchone()[0]
            trial_data.append(imp_entry)
            trial_data.append(location_entry)
            trial_data.append(sponsor_entry)
            ws.append(trial_data)
        wb.save(output_file + ".xlsx")
        another = input('Saved file {}. Continue (Y/N)? > '.format(output_file))
        if another.casefold() != "y":
            break
db.close()
