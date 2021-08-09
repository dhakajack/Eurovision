"""
Take a text listing of clinical trials from the EU clinical trial registry,
extract relevant data, and parse into a relational database for further
exploration.
"""


import re
import sqlite3


def wipe_list(target: list, start: int) -> None:
    """
    Sets the third element of a list to "". Called by wipe_all.
    :param target: A list consisting of field_name, regexp, value
    :param start: Index of first element of list to wipe
    :return:
    """
    for i in range(start, len(target)):
        target[i][FIELD_VAL] = ""


def wipe_all() -> None:
    """
    Reinitializes all database fields except for the Eudract number
    of the current trial.
    :return: None.
    """
    wipe_list(trial, 1)  # skips the eudract number
    wipe_list(drug, 0)
    wipe_list(sponsor, 0)
    # clear the lists that are built per-trial
    drug_list.clear()
    sponsor_set.clear()
    location_set.clear()


def create_databases(filespec: str) -> None:
    """
    Create the relational databases underlying the registry.
    :return: None
    """
    print("Creating databases")  # TODO comment out debug statement

    with sqlite3.connect(filespec) as db:

        db_trial_def = """CREATE TABLE trial1(
        eudract TEXT NOT NULL,
        status TEXT NOT NULL,
        db_date TEXT NOT NULL,
        title TEXT NOT NULL,
        nct TEXT NOT NULL,
        placebo BOOLEAN NOT NULL,
        condition TEXT NOT NULL,
        meddra_version REAL NULL,
        meddra_level TEXT NOT NULL,
        meddra_classification, INTEGER NOT NULL,
        meddra_term TEXT NOT NULL,
        meddra_soc INTEGER NOT NULL,
        rare INTEGER NOT NULL,
        fih INTEGER NOT NULL,
        bioequivalence INTEGER NOT NULL,
        phase1 INTEGER NOT NULL,
        phase2 INTEGER NOT NULL,
        phase3 INTEGER NOT NULL,
        phase4 INTEGER NOT NULL,
        diagnosis INTEGER NOT NULL,
        prophylaxis INTEGER NOT NULL,
        therapy INTEGER NOT NULL,
        safety INTEGER NOT NULL,
        efficacy INTEGER NOT NULL,
        pk INTEGER NOT NULL,
        pd INTEGER NOT NULL,
        randomised INTEGER NOT NULL,
        open_design INTEGER NOT NULL,
        single_blind INTEGER NOT NULL,
        double_blind INTEGER NOT NULL,
        crossover INTEGER NOT NULL,
        age_in_utero INTEGER NOT NULL,
        age_under2 INTEGER NOT NULL,
        age_2to11 INTEGER NOT NULL,
        age_18to64 INTEGER NOT NULL,
        age_65plus INTEGER NOT NULL,
        female INTEGER NOT NULL,
        male INTEGER NOT NULL,
        network TEXT NOT NULL,
        eot_status TEXT NOT NULL,
        eot_date TEXT NOT NULL
        )
        """

        db_drug_def = """CREATE TABLE drug(
        eudract TEXT NOT NULL,
        trade TEXT NOT NULL,
        product TEXT NOT NULL,
        code TEXT NOT NULL,
        inn TEXT NOT NULL,
        cas TEXT NOT NULL,
        sponsor_code TEXT NOT NULL,
        ev_substance TEXT NOT NULL,
        alt_name TEXT NOT NULL
        )
        """

        db_sponsor_def = """CREATE TABLE sponsor(
        eudract TEXT NOT NULL,
        name TEXT NOT NULL,
        org TEXT NOT NULL,
        contact TEXT NOT NULL,
        email TEXT NOT NULL
        )
        """

        db_location_def = """CREATE TABLE location(
        eudract TEXT NOT NULL,
        location TEXT NOT NULL
        )
        """

        db.execute(db_trial_def)
        db.execute(db_drug_def)
        db.execute(db_sponsor_def)
        db.execute(db_location_def)
    db.close()


def update_trial(db):
    """
    Write the core parameters for a given trial (defined by unique
    Eudract number) to database.
    :return:
    """
    print(banner())
    print("Updating trial table")  # TODO comment out debug statement
    for (field_name, regexp, field_value) in trial:
        print("{} = {}".format(field_name, field_value))


def drug_fields_match(okptr: str, currptr: str) -> bool:
    """
    A helper function for update_drug. Determines if drug fields match for the purpose of consolidating
    duplicates
    :param okptr:
    :param currptr:
    :return:
    """
    if len(okptr) > 0 and okptr == currptr:
        return True
    return False


def update_drug(db, list_of_drugs):
    """
    Write the drug data for a given trial to the database.
    :return:
    """
    top_ptr = len(list_of_drugs)
    if top_ptr > 1:
        ok_ptr = 0
        while ok_ptr != top_ptr:
            current_ptr = ok_ptr + 1
            while current_ptr != top_ptr:
                # does any drug field match? Try all except the ALT field ? If so, combine
                if drug_fields_match(list_of_drugs[ok_ptr][0], list_of_drugs[current_ptr][0]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][1], list_of_drugs[current_ptr][1]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][2], list_of_drugs[current_ptr][2]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][3], list_of_drugs[current_ptr][3]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][4], list_of_drugs[current_ptr][4]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][5], list_of_drugs[current_ptr][5]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][6], list_of_drugs[current_ptr][6]):

                    # Take the shorter of the Trade names:
                    if len(list_of_drugs[ok_ptr][0]) > len(list_of_drugs[current_ptr][0]) > 0:
                        list_of_drugs[ok_ptr][0] = list_of_drugs[current_ptr][0]

                    # Take the shorter of the Product names:
                    if len(list_of_drugs[ok_ptr][1]) > len(list_of_drugs[current_ptr][1]) > 0:
                        list_of_drugs[ok_ptr][1] = list_of_drugs[current_ptr][1]

                    # If only one entry has a value for a given field, use it.
                    for i in range(0, len(list_of_drugs[ok_ptr])):
                        if list_of_drugs[ok_ptr][i] == "":
                            list_of_drugs[ok_ptr][i] = list_of_drugs[current_ptr][i]

                    list_of_drugs[current_ptr] = list_of_drugs[top_ptr - 1]
                    top_ptr -= 1
                else:
                    current_ptr += 1
            ok_ptr += 1
    list_of_drugs = list_of_drugs[:top_ptr]
    add_drug_stmt = """INSERT INTO drug(eudract, trade, product, code, inn, cas, sponsor_code, ev_substance, alt_name) 
                    VALUES(?,?,?,?,?,?,?,?,?)"""
    for (trade, product, code, inn, cas, sponsor_code, alt_name, ev_substance) in list_of_drugs:
        db.execute(add_drug_stmt, (trial[0][2],
                                   trade,
                                   product,
                                   code,
                                   inn,
                                   cas,
                                   sponsor_code,
                                   ev_substance,
                                   alt_name)) # This is intentional, want alt listed last in db


def update_sponsor(db):
    """
    Write the sponsor-related data for a given trial to the database.
    :return:
    """
    add_sponsor_stmt = """INSERT INTO sponsor(eudract, name, org, contact, email) 
                        VALUES(?,?,?,?,?)"""
    for (sponsor_name, sponsor_org, sponsor_contact, sponsor_email) in sponsor_set:
        db.execute(add_sponsor_stmt, (trial[0][2],
                                      sponsor_name,
                                      sponsor_org,
                                      sponsor_contact,
                                      sponsor_email))

def update_location(db):
    """
    Write the location-related data about a trial to the database.
    :return:
    """
    print("Updating location table")
    for i in location_set:
        print("Location: {}".format(i))


def add_drug_to_list():
    """
    Add a drug to the list of drug information, even if it duplicates some information.
    :return:
    """
    drug_list.append([drug[0][2].casefold(),    # Trade
                      drug[1][2].casefold(),    # Product
                      drug[2][2].casefold(),    # Code
                      drug[3][2].casefold(),    # INN
                      drug[4][2],               # CAS
                      drug[5][2].casefold(),    # Current Sponsor Code
                      drug[6][2].upper(),       # EV Substance
                      drug[7][2].casefold()     # ALT
                      ])


def add_sponsor_to_set():
    """
    Add a sponsor to the set of sponsor information, even if it duplicates some info.
    :return:
    """
    sponsor_set.add((sponsor[0][2].casefold().title(),      # Name
                     sponsor[1][2].casefold().title(),      # Org
                     sponsor[2][2].casefold().title(),      # Contact
                     sponsor[3][2].casefold()))             # email


def update_databases(filespec):
    """
    Calls subroutines to write data to each table of database.
    :return:
    """
    # Add uncommitted items to their respective lists
    with sqlite3.connect(filespec) as conn:
        add_drug_to_list()
        add_sponsor_to_set()
        # Update each database table
        update_trial(conn)
        update_drug(conn, drug_list)
        update_sponsor(conn)
        update_location(conn)
    conn.close()


def list_match(current_line: str, test_list: list) -> str:
    """
    Looks for the regexp in the current line. If found, it returns the
    captured value, otherwise, an empty string (equivalent to False).

    :param
    current_line: line from file
    test_list:  Read in a list with the following elements:
        - 0: database header term (str)
        - 1: compiled regular expression (regexp object)
        - 2: value (str)
    :return: The captured substring
    """
    m = test_list[1].match(" ".join(current_line.split()))
    if m:
        return m.group(1)
    else:
        return ""


def table_match(current_line: str, test_table: list) -> bool:
    """
    Reads a line from the trial listing and tries to match it against
    regular expressions that define trial elements that are unique to each trial.
    When a match is found, the value is captured and stored back in the list.
    :param current_line: A line from the text listing of trials
    :param test_table: For each table in database, a list of:
        - 0: database header term (str)
        - 1: compiled regular expression (regexp object)
        - 2: value (str)
    :return:
    """
    for i in range(1, len(test_table)):
        # If a element has already been defined, i.e., in an earlier pass through another
        # member-state version of the same trial, skip this. Don't overwrite the non-blank
        # values from the first trial listed
        if test_table[i][2] == "":
            lm = list_match(current_line, test_table[i])
            if lm:
                test_table[i][2] = lm
                return True
    return False


def drug_match(current_line: str, line_count: int) -> bool:
    for i in range(len(drug)):
        current_term = list_match(current_line, drug[i])
        if current_term:
            if line_count < 20:
                drug[i][FIELD_VAL] = current_term
            else:
                if drug[0][FIELD_VAL] != "" \
                  or drug[1][FIELD_VAL] != "" \
                  or drug[2][FIELD_VAL] != "" \
                  or drug[3][FIELD_VAL] != "" \
                  or drug[4][FIELD_VAL] != "" \
                  or drug[5][FIELD_VAL] != "" \
                  or drug[6][FIELD_VAL] != "" \
                  or drug[7][FIELD_VAL] != "":
                    add_drug_to_list()
                    wipe_list(drug, 0)
                drug[i][FIELD_VAL] = current_term
            return True
    return False


def banner(banchar="*", width=80) -> str:
    """ Print a line of some character to break up output"""
    return banchar * width


def parse_listing(infile: str, outfile: str):
    line_scan_count = 100  # just some arbitrary number > 20 to set up first drug read
    with open(infile, "r") as eu_trials:
        line = eu_trials.readline()
        while line:
            line_scan_count += 1
            # For each line, try to match all elements to be captured.
            # Begin with the Eudract number, which signals start of a new trial listing
            tested_term = list_match(line, trial[0])  # Trial Eudract number
            if tested_term:
                # Is this a new trial, or a listing of same trial for different EU member state?
                if trial[0][FIELD_VAL] != tested_term:
                    if trial[0][FIELD_VAL] != "":
                        # write to database tables
                        update_databases(outfile)
                    # Capture the new Eudract number for next trial
                    trial[0][FIELD_VAL] = tested_term
                    # wipe other data elements
                    wipe_all()
                line = eu_trials.readline()
                continue
            if drug_match(line, line_scan_count):
                line_scan_count = 0
                line = eu_trials.readline()
                continue
            tested_term = list_match(line, sponsor[0])  # sponsor
            if tested_term:
                if sponsor[0][FIELD_VAL] != "":
                    add_sponsor_to_set()
                    wipe_list(sponsor, 0)
                sponsor[0][FIELD_VAL] = tested_term
                # sponsor data is collected for each member state instance of a trial because
                # the sponsor and/or contact info can change per memberstate. It is put into
                # a set with the intent of minimizing duplication.
                line = eu_trials.readline()
                continue
            # Locations are defined in two locations: in the header for each member state's instance
            # of a trial and in a list for trials that take place at least partially outside the EEA
            tested_term = location_re.match(" ".join(line.split()))
            if tested_term:
                location_set.add(tested_term.group(1))
                line = eu_trials.readline()
                continue
            tested_term = location_list_start_re.match(line)
            if tested_term:
                line = eu_trials.readline()
                tested_term = location_list_end_re.match(line)
                while not tested_term:
                    location_set.add(" ".join(line.split()))
                    line = eu_trials.readline()
                    tested_term = location_list_end_re.match(line)
                line = eu_trials.readline()
                continue
            # Finally, check for any items that should occur once per trial
            if table_match(line, trial) or table_match(line, sponsor):
                line = eu_trials.readline()
                continue
            # Future expansion: add any new elements here
            line = eu_trials.readline()
        # Flush last record
        update_databases(outfile)


# Compile some regexps at initialization rather than access the supermethod "live"
# within a loop, which would be more expensive computationally

# Compile regexps related to trial elements
trial_eudract_re = re.compile(r"^EudraCT Number:\s*(\S+)")
trial_sponsor_code_re = re.compile("^Sponsor's Protocol Code Number: (.*$)")
trial_status_re = re.compile("^Trial Status: (.*$)")
trial_db_date_re = re.compile("^Date on which this record was first entered in the EudraCT database: (.*$)")
trial_title_re = re.compile("^A.3 Full title of the trial: (.*$)")
trial_NCT_re = re.compile(r"^A.5.2 US NCT \(ClinicalTrials.gov registry\) number: NCT(\d+)")
trial_placebo_re = re.compile(r"D.8.1 Is a Placebo used in this Trial\? (.*$)")
trial_condition_re = re.compile(r"^E.1.1 Medical condition\(s\) being investigated: (.*$)")
trial_MedDRA_version_re = re.compile("^E.1.2 Version: ([0-9.]+)")
trial_MedDRA_level_re = re.compile("^E.1.2 Level: (.*$)")
trial_MedDRA_classification_re = re.compile(r"^E.1.2 Classification code: (\d+)")
trial_MedDRA_term_re = re.compile("^E.1.2 Term: (.*$)")
trial_MedDRA_SOC_re = re.compile(r"^E.1.2 System Organ Class: (\d+)")
trial_rare_re = re.compile("^E.1.3 Condition being studied is a rare disease: (.*$)")
trial_fih_re = re.compile("^E.7.1.1 First administration to humans: (.*$)")
trial_bioequivalence_re = re.compile("^E.7.1.2 Bioequivalence study: (.*$)")
trial_phase1_re = re.compile(r"^E.7.1 Human pharmacology \(Phase I\): (.*$)")
trial_phase2_re = re.compile(r"^E.7.2 Therapeutic exploratory \(Phase II\): (.*$)")
trial_phase3_re = re.compile(r"^E.7.3 Therapeutic confirmatory \(Phase III\): (.*$)")
trial_phase4_re = re.compile(r"^E.7.4 Therapeutic use \(Phase IV\): (.*$)")
trial_scope_diagnosis_re = re.compile("^E.6.1 Diagnosis: (.*$)")
trial_scope_prophylaxis_re = re.compile("^E.6.2 Prophylaxis: (.*$)")
trial_scope_therapy_re = re.compile("^E.6.3 Therapy: (.*$)")
trial_scope_safety_re = re.compile("^E.6.4 Safety: (.*$)")
trial_scope_efficacy_re = re.compile("^E.6.5 Efficacy: (.*$)")
trial_scope_PK_re = re.compile("^E.6.6 Pharmacokinetic: (.*$)")
trial_scope_PD_re = re.compile("^E.6.7 Pharmacodynamic: (.*$)")
trial_scope_randomised_re = re.compile("^E.8.1.1 Randomised: (.*$)")
trial_scope_open_re = re.compile("^E.8.1.2 Open: (.*$)")
trial_scope_single_blind_re = re.compile("^E.8.1.3 Single blind: (.*$)")
trial_scope_double_blind_re = re.compile("^E.8.1.4 Double blind: (.*$)")
trial_scope_crossover_re = re.compile("^E.8.1.6 Cross over: (.*$)")
trial_age_in_utero_re = re.compile("^F.1.1.1 In Utero: (.*$)")
trial_age_preterm_re = re.compile(r"^F.1.1.2 Preterm newborn infants \(up to gestational age < 37 weeks\): (.*$)")
trial_age_newborn_re = re.compile(r"^F.1.1.3 Newborns \(0-27 days\): (.*$)")
trial_age_under2_re = re.compile(r"^F.1.1.4 Infants and toddlers \(28 days-23 months\): (.*$)")
trial_age_2to11_re = re.compile(r"^F.1.1.5 Children \(2-11years\): (.*$)")
trial_age_12to17_re = re.compile(r"^F.1.1.6 Adolescents \(12-17 years\): (.*$)")
trial_age_18to64_re = re.compile(r"^F.1.2 Adults \(18-64 years\): (.*$)")
trial_age_65plus_re = re.compile(r"^F.1.3 Elderly \(>=65 years\): (.*$)")
trial_female_re = re.compile("^F.2.1 Female: (.*$)")
trial_male_re = re.compile("^F.2.2 Male: (.*$)")
trial_network_name_re = re.compile("^G.4.1 Name of Organisation: (.*$)")
trial_end_of_trial_status_re = re.compile("^P. End of Trial Status: (.*$)")
trial_end_of_trial_date_re = re.compile("^P. Date of the global end of the trial: (.*$)")

# Compile regexps related to trial IMP(s)
imp_trade_name_re = re.compile("^D.2.1.1.1 Trade name: (.*$)")
imp_name_re = re.compile("^D.3.1 Product name: (.*$)")
imp_code_re = re.compile("^D.3.2 Product code: (.*$)")
imp_inn_re = re.compile("^D.3.8 INN - Proposed INN: (.*$)")
imp_cas_re = re.compile(r"^D.3.9.1 CAS number:\s+(\d{2,7}-\d{2}-\d)")
imp_sponsor_code = re.compile("D.3.9.2 Current sponsor code: (.*$)")
imp_alt_names_re = re.compile("^D.3.9.3 Other descriptive name: (.*$)")
imp_ev_substance_re = re.compile("^D.3.9.4 EV Substance Code: (.*$)")

# Compile regexps related to trial sponsor
sponsor_name_re = re.compile("^B.1.1 Name of Sponsor: (.*$)")
sponsor_org_re = re.compile("^B.5.1 Name of organisation: (.*$)")
sponsor_contact_re = re.compile("^B.5.2 Functional name of contact point: (.*$)")
sponsor_email_re = re.compile(r"^B.5.6 E-mail:\s*(\S+@\S+[.]\S+)\s*$")


# Compile regexps related to trial location
location_re = re.compile(r"^National Competent Authority:\s+(\S*)\s+[-]")
location_list_start_re = re.compile("^E.8.6.3 If E.8.6.1 or E.8.6.2 are Yes")
location_list_end_re = re.compile("^E.8.7 Trial has a data monitoring committee")

# Lists that define all of the once-per-trial elements to be extracted follow
# the same structure:
FIELD_NAME = 0  # name used in database header
REGEXP_REF = 1  # name assigned to each compiled regular expression, above
FIELD_VAL = 2   # the value extracted

# List of unique elements to extract to the Trial table for each trial
trial = [["eudract", trial_eudract_re, ""],
         ["sponsor_code", trial_sponsor_code_re, ""],
         ["status", trial_status_re, ""],
         ["db_date", trial_db_date_re, ""],
         ["title", trial_title_re, ""],
         ["NCT", trial_NCT_re, ""],
         ["placebo", trial_placebo_re, ""],
         ["condition", trial_condition_re, ""],
         ["MedDRA_Version", trial_MedDRA_version_re, ""],
         ["MedDRA_level", trial_MedDRA_level_re, ""],
         ["MedDRA_classification", trial_MedDRA_classification_re, ""],
         ["MedDRA_term", trial_MedDRA_term_re, ""],
         ["MedDRA_SOC", trial_MedDRA_SOC_re, ""],
         ["rare", trial_rare_re, ""],
         ["fih", trial_fih_re, ""],
         ["bioequivalence", trial_bioequivalence_re, ""],
         ["phase1", trial_phase1_re, ""],
         ["phase2", trial_phase2_re, ""],
         ["phase3", trial_phase3_re, ""],
         ["phase4", trial_phase4_re, ""],
         ["diagnosis", trial_scope_diagnosis_re, ""],
         ["prophylaxis", trial_scope_prophylaxis_re, ""],
         ["scope_therapy", trial_scope_therapy_re, ""],
         ["scope_safety", trial_scope_safety_re, ""],
         ["scope_efficacy", trial_scope_efficacy_re, ""],
         ["scope_PK", trial_scope_PK_re, ""],
         ["scope_PD", trial_scope_PD_re, ""],
         ["randomised", trial_scope_randomised_re, ""],
         ["open_design", trial_scope_open_re, ""],
         ["single_blind", trial_scope_single_blind_re, ""],
         ["double_blind", trial_scope_double_blind_re, ""],
         ["crossover", trial_scope_crossover_re, ""],
         ["age_in_utero", trial_age_in_utero_re, ""],
         ["age_preterm", trial_age_preterm_re, ""],
         ["age_newborn", trial_age_newborn_re, ""],
         ["age_under2", trial_age_under2_re, ""],
         ["age_2to11", trial_age_2to11_re, ""],
         ["age12to17", trial_age_12to17_re, ""],
         ["age18to64", trial_age_18to64_re, ""],
         ["age_65plus", trial_age_65plus_re, ""],
         ["female", trial_female_re, ""],
         ["male", trial_male_re, ""],
         ["network", trial_network_name_re, ""],
         ["EOT_status", trial_end_of_trial_status_re, ""],
         ["EOT_date", trial_end_of_trial_date_re, ""]]

# List of unique elements to extract to the Drug table for each trial
drug = [["trade_name", imp_trade_name_re, ""],
        ["product_name", imp_name_re, ""],
        ["product_code", imp_code_re, ""],
        ["inn", imp_inn_re, ""],
        ["cas", imp_cas_re, ""],
        ["sponsor_code", imp_sponsor_code, ""],
        ["ev_substance", imp_ev_substance_re, ""],
        ["imp_alt_names", imp_alt_names_re, ""]]

# List of unique elements to extract to the Sponsor table for each trial
sponsor = [["sponsor_name", sponsor_name_re, ""],
           ["sponsor_org", sponsor_org_re, ""],
           ["sponsor_contact", sponsor_contact_re, ""],
           ["sponsor_email", sponsor_email_re, ""]]

# Sets are used for sponsor and location to consolidate repeating data
drug_list = []
sponsor_set = set()
location_set = set()

source_file = "test2000x.txt"
database_name = input("Name of database to write? > ")
create_databases(database_name)
parse_listing(source_file, database_name)
