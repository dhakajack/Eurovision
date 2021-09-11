"""
Take a text listing of clinical trials from the EU clinical trial registry,
extract relevant data, and parse into a relational database for further
exploration.
"""


import re
import sqlite3
import time


class Element:

    def __init__(self, field_type: str, regdef: str):
        self.field_type = field_type                    # database data type e.g. "TEXT NOT NULL"
        self.regdef = regdef                            # regular expression pattern
        self.regexpdef = re.compile(regdef)             # regex is compiled at instantiation
        self.value = ""                                 # holds value read from source file


def wipe_dict(target: dict) -> None:
    """
    Sets the value of a dictionary element to "". Called by wipe_all.
    :param target: A dictionary with elements.
    :return:
    """
    for item in target:
        target[item].value = ""


def wipe_all() -> None:
    """
    Reinitializes all database fields.
    :return: None.
    """
    wipe_dict(trial)
    wipe_dict(imp)
    wipe_dict(sponsor)
    # clear the lists that are built per-trial
    imp_list.clear()
    sponsor_set.clear()
    location_set.clear()


def create_databases(filespec: str) -> None:
    """
    Create the relational databases underlying the registry.
    :return: None
    """
    print("Creating databases")

    with sqlite3.connect(filespec) as db:
        db_trial_def = "CREATE TABLE trial(\n{}\n)"

        db_imp_def = "CREATE TABLE imp(\n" \
                     "eudract_id TEXT NOT NULL," \
                     "\n{}\n" \
                     ")"

        db_sponsor_def = "CREATE TABLE sponsor(\n" \
                         "eudract_id TEXT NOT NULL," \
                         "\n{}\n" \
                         ")"

        db_location_def = "CREATE TABLE location(\n" \
                          "eudract_id TEXT NOT NULL,\n" \
                          "location TEXT NOT NULL\n" \
                          ")"

        db_location_index = "CREATE INDEX idx_location on location (eudract_id)"
        db_sponsor_index = "CREATE INDEX idx_imp on imp (eudract_id)"
        db_imp_index = "CREATE INDEX idx_sponsor on sponsor (eudract_id)"

        db.execute(db_trial_def
                   .format(", \n".join(["{} {}".format(x, trial[x].field_type) for x in sorted(trial)])))
        db.execute(db_imp_def
                   .format(", \n".join(["{} {}".format(x, imp[x].field_type) for x in sorted(imp)])))
        db.execute(db_sponsor_def
                   .format(", \n".join(["{} {}" .format(x, sponsor[x].field_type) for x in sorted(sponsor)])))
        db.execute(db_location_def)
        db.execute(db_location_index)
        db.execute(db_sponsor_index)
        db.execute(db_imp_index)
        print("databases created!")
    db.close()


def update_trial(db: sqlite3.Connection) -> None:
    """
    Write the core parameters for a given trial (defined by unique
    Eudract number) to database. Uses replacement fields, which may
    be overkill, but just in case anyone actually managed to stick
    some SQL into the trial registry itself.
    :return:
    """
    # Consistency check: Trial status is often not updated in one or more
    # records for a trial. If any MS entry lists a completion date, we do
    # not know how the trial ended, but can be pretty sure that it did end. The status
    # of 'not ongoing' is not a native value for this field to make it obvious that
    # this was imputed during curation.

    if trial["completion_date"].value and trial["overall_status"].value == "ongoing":
        trial["overall_status"].value = "not ongoing"

    # If the meddra level is SOC rather than the expected PT, LLT, etc.,
    # and there is no entry for the meddra SOC, copy the classification
    # into the SOC field

    if not trial["meddra_soc"].value and trial["meddra_level"].value == "soc":
        trial["meddra_soc"].value = trial["meddra_classification"].value

    print("Updating trial {}".format(trial["eudract_id"].value))

    for x in [prop for prop in trial if trial[prop].field_type == "INTEGER NOT NULL"]:
        if trial[x].value == "yes":
            trial[x].value = 1
        elif trial[x].value == "no":
            trial[x].value = 0

    add_trial_stmt = """INSERT INTO trial(
                        {})
                        VALUES({})"""

    try:
        db.execute(add_trial_stmt
                   .format(", \n".join(sorted(trial)), ",".join("?" * len(trial))),
                   [trial[x].value for x in sorted(trial)])
    except sqlite3.IntegrityError:
        print("Database integrity error, likely duplicate Eudract number for study {}"
              .format(trial["eudract_id"].value))
        # This can happen if the database "wraps" on last page displayed


def imp_fields_match(okptr: str, currptr: str) -> bool:
    """
    A helper function for update_imp. Determines if IMP fields match for the purpose of consolidating
    duplicates
    :param okptr:
    :param currptr:
    :return: Whether the fields match.
    """
    if len(okptr) > 0 and okptr == currptr:
        return True
    return False


def update_imp(db: sqlite3.Connection, list_of_imps) -> None:
    """
    Write the IMP data for a given trial to the database.
    :return: None.
    """
    # Sort through IMP entries, possibly representing one or several IMPs in the trial to
    # eliminate duplicates. When one entry contains information for a given IMP not present
    # in other entries, harvest that information so the final list for each IMP combines
    # all information available for that IMP.
    top_ptr = len(list_of_imps)
    if top_ptr > 1:
        ok_ptr = 0
        while ok_ptr != top_ptr:
            current_ptr = ok_ptr + 1
            while current_ptr != top_ptr:
                # does any IMP field match? If so, combine
                if imp_fields_match(list_of_imps[ok_ptr][0], list_of_imps[current_ptr][0]) \
                  or imp_fields_match(list_of_imps[ok_ptr][1], list_of_imps[current_ptr][1]) \
                  or imp_fields_match(list_of_imps[ok_ptr][2], list_of_imps[current_ptr][2]):

                    # Take the shorter of the Trade names:
                    if len(list_of_imps[ok_ptr][0]) > len(list_of_imps[current_ptr][0]) > 0:
                        list_of_imps[ok_ptr][0] = list_of_imps[current_ptr][0]

                    # Take the shorter of the Product names:
                    if len(list_of_imps[ok_ptr][1]) > len(list_of_imps[current_ptr][1]) > 0:
                        list_of_imps[ok_ptr][1] = list_of_imps[current_ptr][1]

                    # If only one entry has a value for a given field, use it.
                    for i in range(0, len(list_of_imps[ok_ptr])):
                        if list_of_imps[ok_ptr][i] == "":
                            list_of_imps[ok_ptr][i] = list_of_imps[current_ptr][i]

                    list_of_imps[current_ptr] = list_of_imps[top_ptr - 1]
                    top_ptr -= 1
                else:
                    current_ptr += 1
            ok_ptr += 1
    # Slice the list down to just the unique IMP entries and write to database
    list_of_imps = list_of_imps[:top_ptr]
    tup_to_db(db, "imp", imp, list_of_imps)


def update_sponsor(db: sqlite3.Connection) -> None:
    """
    Write the sponsor-related data for a given trial to the database.
    :return: None.
    """
    tup_to_db(db, "sponsor", sponsor, sponsor_set)


def tup_to_db(db: sqlite3.Connection, tup_name: str, tup_dict: dict, tups) -> None:
    """
    Helper function that takes care of database writing for update_sponsor
    and update_imp.
    :param db: the database connection
    :param tup_name: string name of the dictionary
    :param tup_dict: the dictionary itself
    :param tups: a tuple from the collection, either the list of IMPs or
    the set of sponsors.
    :return: None.
    """
    add_tup_stmt = "INSERT INTO {}({})\nVALUES({})"
    for details in tups:
        temp = list(details)
        temp.insert(0, trial["eudract_id"].value)
        db.execute(add_tup_stmt.format(tup_name,
                                       "\neudract_id,\n" + ",\n".join(sorted(tup_dict)),
                                       ",".join("?" * (len(tup_dict) + 1))),
                   tuple(temp))


def update_location(db: sqlite3.Connection) -> None:
    """
    Write the location-related data about a trial to the database.
    :return: None.
    """
    add_location_stmt = "INSERT INTO location(eudract_id, location)\nVALUES(?,?)"
    for where in sorted(location_set):
        db.execute(add_location_stmt, (trial["eudract_id"].value,
                                       where))


def add_imp_to_list() -> None:
    """
    Add an IMP to the list of IMP information, even if it duplicates some information.
    :return: None. Modifies the IMP list.
    """
    # if there is something in any of the fields, add that entry to the IMP list
    imp_list.append([imp["trade"].value,
                     imp["product"].value,
                     imp["code"].value,
                     ])


def add_sponsor_to_set() -> None:
    """
    Add a sponsor to the set of sponsor information, even if it duplicates some info.
    :return: None. Updates the sponsor set.
    """
    sponsor_set.add(tuple([sponsor[x].value.title() if x != "email" else sponsor[x].value for x in sorted(sponsor)]))


def empty_dict(query_dict: dict) -> bool:
    """
    Determine if a dict (e.g., IMP) has no data. Sometimes trials have no IMP at all listed,
    in other cases, the IMP section may have an entry without an IMP-identifing information.
    :return: True if any of the dictionary elements are defined.
    """
    for item in query_dict:
        if query_dict[item].value != "":
            return False
    return True


def update_databases(filespec: str) -> None:
    """
    Calls subroutines to write data to each table of database.
    :return:
    """
    # Add uncommitted items to their respective lists
    with sqlite3.connect(filespec) as conn:
        if not empty_dict(imp):
            add_imp_to_list()
        add_sponsor_to_set()
        # Update each database table
        update_trial(conn)
        update_imp(conn, imp_list)
        update_sponsor(conn)
        update_location(conn)
    conn.close()


def table_match(current_line: str, dict_item: dict, dict_item_keys: list) -> bool:
    """
    Reads a line from the trial listing and tries to match it against
    regular expressions that define trial elements. When a match is found, the
    value is captured and stored back in the list. Caveat: Where the database
    is not consistent, this value may not be reliable. This algorithm favours
    responses with some content over null responses and for yes/no fields, will
    take a yes over a no.
    :param current_line: A line from the text listing of trials
    :param dict_item: A dictionary with data elements
    :param dict_item_keys: A subset of dictionary keys to evaluate
    :return: Whether a match was found
    """
    for key in dict_item_keys:
        # Don't override previously defined data elements except a "yes"
        # trumps a "no" reply
        if dict_item[key] == "no":
            lm = list_match(current_line, dict_item[key])
            if lm == "yes":
                dict_item[key].value = "yes"
                return True
        elif dict_item[key].value == "":
            lm = list_match(current_line, dict_item[key])
            if lm:
                dict_item[key].value = lm
                return True
    return False


def list_match(current_line: str, test_item: Element) -> str:
    """
    Looks for the regexp in the current line. If found, it returns the
    captured value, otherwise, an empty string (equivalent to False).

    :param
    current_line: line from file
    test_item: a table item to check for a match
    :return: The captured substring
    """
    m = test_item.regexpdef.match(" ".join(current_line.split()))
    if m:
        if test_item.regexpdef == trial["official_title"].regexpdef:
            return m.group(1)  # i.e., don't casefold the study title.
        else:
            return m.group(1).casefold()
    else:
        return ""


def parse_listing(infile: str, outfile: str):
    current_trial = ""
    print("Parsing.")
    with open(infile, "r", encoding='utf8') as eu_trials:
        line = eu_trials.readline()
        while line:
            if not any(screen_item in line for screen_item in screening_list):
                line = eu_trials.readline()
                continue
            # For each line, try to match all elements to be captured.
            # Begin with the Eudract number, which signals start of a new trial listing
            tested_term = list_match(line, trial["eudract_id"])  # Trial Eudract number
            if tested_term:
                # Is this a new trial, or a listing of same trial for different EU member state?
                if current_trial != tested_term:
                    if trial["eudract_id"].value != "":
                        # write to database tables
                        update_databases(outfile)
                    # Capture the new Eudract number for next trial
                    wipe_all()
                    trial["eudract_id"].value = current_trial = tested_term
                line = eu_trials.readline()
                continue
            tested_term = other["imp_re"].regexpdef.match(" ".join(line.split()))
            if tested_term:
                if not empty_dict(imp):
                    add_imp_to_list()
                    wipe_dict(imp)
                line = eu_trials.readline()
                continue
            tested_term = list_match(line, sponsor["name"])  # sponsor
            if tested_term:
                if sponsor["name"].value != "":
                    add_sponsor_to_set()
                    wipe_dict(sponsor)
                sponsor["name"].value = tested_term
                # sponsor data is collected for each member state instance of a trial because
                # the sponsor and/or contact info can change per member state. It is put into
                # a set with the intent of minimizing duplication.
                line = eu_trials.readline()
                continue
            # Locations are defined in two locations: in the header for each member state's instance
            # of a trial and in a list for trials that take place at least partially outside the EEA
            tested_term = other["loc_re"].regexpdef.match(" ".join(line.split()))
            if tested_term:
                location_set.add(tested_term.group(1))
                line = eu_trials.readline()
                continue
            tested_term = other["loc_start_re"].regexpdef.match(line)
            if tested_term:
                line = eu_trials.readline()
                tested_term = other["loc_end_re"].regexpdef.match(line)
                while not tested_term:
                    location_set.add(" ".join(line.split()))
                    line = eu_trials.readline()
                    tested_term = other["loc_end_re"].regexpdef.match(line)
                line = eu_trials.readline()
                continue
            tested_term = other["loc_alt_start_re"].regexpdef.match(line)
            if tested_term:
                line = eu_trials.readline()
                tested_term = other["loc_alt_end_re"].regexpdef.match(line)
                while not tested_term:
                    location_set.add(" ".join(line.split()))
                    line = eu_trials.readline()
                    tested_term = other["loc_alt_end_re"].regexpdef.match(line)
                line = eu_trials.readline()
                continue
            # Finally, fill these tables
            if table_match(line, trial, [x for x in trial if x != "eudract_id"]) \
                    or table_match(line, imp, [x for x in imp]) \
                    or table_match(line, sponsor, [x for x in sponsor if x != "name"]):
                line = eu_trials.readline()
                continue
            # Future expansion: add any new elements here
            line = eu_trials.readline()
        # Flush last record
        update_databases(outfile)


# Trial dictionary definitions
trial = {"eudract_id": Element("TEXT NOT NULL PRIMARY KEY", r"^EudraCT Number:\s*(\S+)"),
         "overall_status": Element("TEXT NOT NULL", "^Trial Status: (.*$)"),
         "study_first_submitted_date": Element("TEXT NOT NULL",
                                               "^Date on which this record was first "
                                               "entered in the EudraCT database: (.*$)"),
         "official_title": Element("TEXT NOT NULL", "^A.3 Full title of the trial: (.*$)"),
         "sponsor_id": Element("TEXT NOT NULL", "^A.4.1 Sponsor's protocol code number: (.*$)"),
         "isrctn_id": Element("TEXT NOT NULL",
                              r"^A.5.1 ISRCTN \(International Standard Randomised Controlled Trial\) number: (.*$)"),
         "who_utrn_id": Element("TEXT NOT NULL",
                                r"^A.5.3 WHO Universal Trial Reference Number \(UTRN\): (.*$)"),
         "nct_id": Element("TEXT NOT NULL", r"^A.5.2 US NCT \(ClinicalTrials.gov registry\) number: (NCT\d+)"),
         "placebo": Element("INTEGER NOT NULL", r"D.8.1 Is a Placebo used in this Trial\? (.*$)"),
         "condition": Element("TEXT NOT NULL", r"^E.1.1 Medical condition\(s\) being investigated: (.*$)"),
         "meddra_version": Element("TEXT NOT NULL", "^E.1.2 Version: ([0-9.]+)"),
         "meddra_level": Element("TEXT NOT NULL", "^E.1.2 Level: (.*$)"),
         "meddra_classification": Element("TEXT NOT NULL", r"^E.1.2 Classification code: (\d+)"),
         "meddra_term": Element("TEXT NOT NULL", "^E.1.2 Term: (.*$)"),
         "meddra_soc": Element("TEXT NOT NULL", r"^E.1.2 System Organ Class: (\d+)"),
         "rare": Element("INTEGER NOT NULL", "^E.1.3 Condition being studied is a rare disease: (.*$)"),
         "fih": Element("INTEGER NOT NULL", "^E.7.1.1 First administration to humans: (.*$)"),
         "bioequivalence": Element("INTEGER NOT NULL", "^E.7.1.2 Bioequivalence study: (.*$)"),
         "phase1": Element("INTEGER NOT NULL", r"^E.7.1 Human pharmacology \(Phase I\): (.*$)"),
         "phase2": Element("INTEGER NOT NULL", r"^E.7.2 Therapeutic exploratory \(Phase II\): (.*$)"),
         "phase3": Element("INTEGER NOT NULL", r"^E.7.3 Therapeutic confirmatory \(Phase III\): (.*$)"),
         "phase4": Element("INTEGER NOT NULL", r"^E.7.4 Therapeutic use \(Phase IV\): (.*$)"),
         "diagnosis": Element("INTEGER NOT NULL", "^E.6.1 Diagnosis: (.*$)"),
         "prophylaxis": Element("INTEGER NOT NULL", "^E.6.2 Prophylaxis: (.*$)"),
         "therapy": Element("INTEGER NOT NULL", "^E.6.3 Therapy: (.*$)"),
         "safety": Element("INTEGER NOT NULL", "^E.6.4 Safety: (.*$)"),
         "efficacy": Element("INTEGER NOT NULL", "^E.6.5 Efficacy: (.*$)"),
         "pk": Element("INTEGER NOT NULL", "^E.6.6 Pharmacokinetic: (.*$)"),
         "pd": Element("INTEGER NOT NULL", "^E.6.7 Pharmacodynamic: (.*$)"),
         "randomised": Element("INTEGER NOT NULL", "^E.8.1.1 Randomised: (.*$)"),
         "open_design": Element("INTEGER NOT NULL", "^E.8.1.2 Open: (.*$)"),
         "single_blind": Element("INTEGER NOT NULL", "^E.8.1.3 Single blind: (.*$)"),
         "double_blind": Element("INTEGER NOT NULL", "^E.8.1.4 Double blind: (.*$)"),
         "crossover": Element("INTEGER NOT NULL", "^E.8.1.6 Cross over: (.*$)"),
         "age_in_utero": Element("INTEGER NOT NULL", "^F.1.1.1 In Utero: (.*$)"),
         "age_preterm": Element("INTEGER NOT NULL",
                                r"^F.1.1.2 Preterm newborn infants \(up to gestational age < 37 weeks\): (.*$)"),
         "age_newborn": Element("INTEGER NOT NULL", r"^F.1.1.3 Newborns \(0-27 days\): (.*$)"),
         "age_under2": Element("INTEGER NOT NULL", r"^F.1.1.4 Infants and toddlers \(28 days-23 months\): (.*$)"),
         "age_2to11": Element("INTEGER NOT NULL", r"^F.1.1.5 Children \(2-11years\): (.*$)"),
         "age12to17": Element("INTEGER NOT NULL", r"^F.1.1.6 Adolescents \(12-17 years\): (.*$)"),
         "age18to64": Element("INTEGER NOT NULL", r"^F.1.2 Adults \(18-64 years\): (.*$)"),
         "age_65plus": Element("INTEGER NOT NULL", r"^F.1.3 Elderly \(>=65 years\): (.*$)"),
         "female": Element("INTEGER NOT NULL", "^F.2.1 Female: (.*$)"),
         "male": Element("INTEGER NOT NULL", "^F.2.2 Male: (.*$)"),
         "enrollment": Element("TEXT NOT NULL", "^F.4.2.2 In the whole clinical trial: (.*$)"),
         "network": Element("TEXT NOT NULL", "^G.4.1 Name of Organisation: (.*$)"),
         "completion_date": Element("TEXT NOT NULL", "^P. Date of the global end of the trial: (.*$)")}

# IMP table definitions
imp = {"trade": Element("TEXT NOT NULL", "^D.2.1.1.1 Trade name: (.*$)"),
       "product": Element("TEXT NOT NULL", "^D.3.1 Product name: (.*$)"),
       "code": Element("TEXT NOT NULL", "^D.3.2 Product code: (.*$)")}

# Sponsor table definitions
sponsor = {"name": Element("TEXT NOT NULL", "^B.1.1 Name of Sponsor: (.*$)"),
           "org": Element("TEXT NOT NULL", "^B.5.1 Name of organisation: (.*$)"),
           "contact": Element("TEXT NOT NULL", "^B.5.2 Functional name of contact point: (.*$)"),
           "email": Element("TEXT NOT NULL", r"^B.5.6 E-mail:\s*(\S+@\S+[.]\S+)\s*$")}

# Other regexp definitions for precompiling:
other = {"imp_re": Element("", r"D.IMP: \d+"),
         "loc_re": Element("", r"^National Competent Authority:\s+(\S*)\s+[-]"),
         "loc_start_re": Element("", "^E.8.6.3 If E.8.6.1 or E.8.6.2 are Yes"),
         "loc_end_re": Element("", "^E.8.7 Trial has a data monitoring committee"),
         "loc_alt_start_re": Element("", "^E.8.6.3 Specify the countries outside of the EEA"),
         "loc_alt_end_re": Element("", "^E.8.7 Trial has a data monitoring committee:")
         }

if __name__ == "__main__":
    # Sets are used for sponsor and location to consolidate repeating data
    imp_list = []
    sponsor_set = set()
    location_set = set()

    # compile a screening list - when parsing, will skip any line without one of these phrases
    screening_list = []
    for dictionary in (trial, imp, sponsor, other):
        for dict_idx in dictionary:
            # first seven characters of each line after removing the regex start of line anchor
            screening_list.append(dictionary[dict_idx].regdef[:7].strip("^"))

    # source_file = "20210826-1644.txt"
    source_file = input("Name of source file to parse? >")
    database_name = input("Name of database to write? > ")
    start_time = time.time()
    create_databases(database_name)
    parse_listing(source_file, database_name)
    print("Run time: {}".format(time.time() - start_time))
