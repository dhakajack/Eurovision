"""
Take a text listing of clinical trials from the EU clinical trial registry,
extract relevant data, and parse into a relational database for further
exploration.
"""


import re
import sqlite3
import time

# Lists that define attributes of the trial itself, drugs, and sponsors all follow
# the same structure:
FIELD_NAME = 0  # name used in database header
FIELD_TYPE = 1  # type of field for database; e.g., TEXT NOT NULL
FIELD_VAL = 2   # the value extracted
REGEXP_REF = 3  # name assigned to each compiled regular expression, above


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
    print("Creating databases")

    with sqlite3.connect(filespec) as db:
        db_trial_def = """CREATE TABLE trial(
        {}
        )
        """

        db_drug_def = """CREATE TABLE drug(
        eudract TEXT NOT NULL,
        {}
        )
        """

        db_sponsor_def = """CREATE TABLE sponsor(
        eudract TEXT NOT NULL,
        {}
        )
        """

        db_location_def = """CREATE TABLE location(
        eudract TEXT NOT NULL,
        location TEXT NOT NULL
        )
        """

        db_location_index = "CREATE INDEX idx_location on location (eudract)"
        db_sponsor_index = "CREATE INDEX idx_drug on drug (eudract)"
        db_drug_index = "CREATE INDEX idx_sponsor on sponsor (eudract)"

        db.execute(db_trial_def.format(", \n".join([" ".join(x[FIELD_NAME:FIELD_VAL]) for x in trial])))
        db.execute(db_drug_def.format(", \n".join([" ".join(x[FIELD_NAME:FIELD_VAL]) for x in drug])))
        db.execute(db_sponsor_def.format(", \n".join([" ".join(x[FIELD_NAME:FIELD_VAL]) for x in sponsor])))
        db.execute(db_location_def)
        db.execute(db_location_index)
        db.execute(db_sponsor_index)
        db.execute(db_drug_index)
    db.close()


def y_n_to_int(answer: str) -> int:
    """
    Helper function to convert "Yes" to 1, which is how boolean True is recorded in sqlite; any
    other value including "" is taken as a False. Case insensitive.
    :param answer: "Yes" or anything other string.
    :return: 1 or 0 for yes or no.
    """
    if answer.casefold() == "yes":
        return 1
    else:
        return 0


def update_trial(db) -> None:
    """
    Write the core parameters for a given trial (defined by unique
    Eudract number) to database. Uses replacement fields, which may
    be overkill, but just in case anyone actually managed to stick
    some SQL into the drug registry itself.
    :return:
    """
    # Consistency check: Trial status (trial[2] is often not updated in one or more
    # records for a trial. If any MS entry lists a completion date (trial[43], we do
    # not know how the trial ended, but can be pretty sure that it did end. The status
    # of 'not ongoing' is not a native value for this field to make it obvious that
    # this was imputed during curation.

    if(trial[43][FIELD_VAL]) and trial[2][FIELD_VAL].casefold() == "ongoing":
        trial[2][FIELD_VAL] = "Not Ongoing"

    # If the meddra level is SOC rather than the expected PT, LLT, etc.,
    # and there is no entry for the meddra SOC, copy the classification
    # into the SOC field

    if not trial[12][FIELD_VAL] and trial[9][FIELD_VAL].casefold() == "soc":
        trial[12][FIELD_VAL] = trial[10][FIELD_VAL]

    print("Updating trial {}".format(trial[0][FIELD_VAL]))
    add_trial_stmt = """INSERT INTO trial(
                        {}) 
                        VALUES({})"""

    try:
        db.execute(add_trial_stmt.format(", \n".join([x[FIELD_NAME] for x in trial]), ",".join("?" * len(trial))), (
                   trial[0][FIELD_VAL],                 # eudract
                   trial[1][FIELD_VAL],                 # sponsor
                   trial[2][FIELD_VAL],                 # status
                   trial[3][FIELD_VAL],                 # db_date
                   trial[4][FIELD_VAL],                 # title
                   trial[5][FIELD_VAL],                 # sponsor_protocol
                   trial[6][FIELD_VAL],                 # isrctn
                   trial[7][FIELD_VAL],                 # who_utrn
                   trial[8][FIELD_VAL],                 # nct
                   y_n_to_int(trial[9][FIELD_VAL]),     # placebo
                   trial[10][FIELD_VAL],                # condition
                   trial[11][FIELD_VAL],                # meddra_version
                   trial[12][FIELD_VAL],                # meddra_level
                   trial[13][FIELD_VAL],                # meddra_classification
                   trial[14][FIELD_VAL],                # meddra_term
                   trial[15][FIELD_VAL],                # meddra_soc
                   y_n_to_int(trial[16][FIELD_VAL]),    # rare
                   y_n_to_int(trial[17][FIELD_VAL]),    # fih
                   y_n_to_int(trial[18][FIELD_VAL]),    # bioequivalence
                   y_n_to_int(trial[19][FIELD_VAL]),    # phase1
                   y_n_to_int(trial[20][FIELD_VAL]),    # phase2
                   y_n_to_int(trial[21][FIELD_VAL]),    # phase3
                   y_n_to_int(trial[22][FIELD_VAL]),    # phase4
                   y_n_to_int(trial[23][FIELD_VAL]),    # diagnosis
                   y_n_to_int(trial[24][FIELD_VAL]),    # prophylaxis
                   y_n_to_int(trial[25][FIELD_VAL]),    # therapy
                   y_n_to_int(trial[26][FIELD_VAL]),    # safety
                   y_n_to_int(trial[27][FIELD_VAL]),    # efficacy
                   y_n_to_int(trial[28][FIELD_VAL]),    # pk
                   y_n_to_int(trial[29][FIELD_VAL]),    # pd
                   y_n_to_int(trial[30][FIELD_VAL]),    # randomised
                   y_n_to_int(trial[31][FIELD_VAL]),    # open_design
                   y_n_to_int(trial[32][FIELD_VAL]),    # single_blind
                   y_n_to_int(trial[33][FIELD_VAL]),    # double_blind
                   y_n_to_int(trial[34][FIELD_VAL]),    # crossover
                   y_n_to_int(trial[35][FIELD_VAL]),    # age_in_utero
                   y_n_to_int(trial[36][FIELD_VAL]),    # age_preterm
                   y_n_to_int(trial[37][FIELD_VAL]),    # age_newborn
                   y_n_to_int(trial[38][FIELD_VAL]),    # age_under2
                   y_n_to_int(trial[39][FIELD_VAL]),    # age_2to11
                   y_n_to_int(trial[40][FIELD_VAL]),    # age_12to17
                   y_n_to_int(trial[41][FIELD_VAL]),    # age_18to64
                   y_n_to_int(trial[42][FIELD_VAL]),    # age_65plus
                   y_n_to_int(trial[43][FIELD_VAL]),    # female
                   y_n_to_int(trial[44][FIELD_VAL]),    # male
                   trial[45][FIELD_VAL],                # n
                   trial[46][FIELD_VAL],                # network
                   trial[47][FIELD_VAL]                 # eot_date
                   ))
    except sqlite3.IntegrityError:
        print("Database integrity error, likely duplicate Eudract number for study {}"
              .format(trial[0][FIELD_VAL]))


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
    # Sort through drug entries, possibly representing one or several drugs in the trial to
    # eliminate duplicates. When one entry contains information for a given drug not present
    # in other entries, harvest that information so the final list for each drug combines
    # all information available for that drug.
    top_ptr = len(list_of_drugs)
    if top_ptr > 1:
        ok_ptr = 0
        while ok_ptr != top_ptr:
            current_ptr = ok_ptr + 1
            while current_ptr != top_ptr:
                # does any drug field match? Try all except the ALT field ? If so, combine
                if drug_fields_match(list_of_drugs[ok_ptr][0], list_of_drugs[current_ptr][0]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][1], list_of_drugs[current_ptr][1]) \
                  or drug_fields_match(list_of_drugs[ok_ptr][2], list_of_drugs[current_ptr][2]):

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
    # Slice the list down to just the unique drug entries and write to database
    list_of_drugs = list_of_drugs[:top_ptr]
    add_drug_stmt = """INSERT INTO drug(eudract, {}) 
                    VALUES({})"""
    for (trade, product, code) in list_of_drugs:
        db.execute(add_drug_stmt.format(", \n".join([x[FIELD_NAME] for x in drug]), ",".join("?" * (len(drug) + 1))),
                   (trial[0][FIELD_VAL],
                    trade,
                    product,
                    code))


def update_sponsor(db):
    """
    Write the sponsor-related data for a given trial to the database.
    :return:
    """
    add_sponsor_stmt = """INSERT INTO sponsor(eudract, {}) 
                        VALUES(?,?,?,?,?)"""
    for (sponsor_name, sponsor_org, sponsor_contact, sponsor_email) in sponsor_set:
        db.execute(add_sponsor_stmt.format(", \n".join([x[FIELD_NAME] for x in sponsor])),
                   (trial[0][FIELD_VAL],
                    sponsor_name,
                    sponsor_org,
                    sponsor_contact,
                    sponsor_email))


def update_location(db):
    """
    Write the location-related data about a trial to the database.
    :return:
    """
    add_location_stmt = """INSERT INTO location(eudract, location)
                            VALUES(?,?)"""
    for where in sorted(location_set):
        db.execute(add_location_stmt, (trial[0][FIELD_VAL],
                                       where))


def add_drug_to_list():
    """
    Add a drug to the list of drug information, even if it duplicates some information.
    :return:
    """
    # if there is something in any of the fields, add that entry to the drug list
    drug_list.append([drug[0][FIELD_VAL].casefold(),    # Trade
                      drug[1][FIELD_VAL].casefold(),    # Product
                      drug[2][FIELD_VAL].casefold(),    # Code
                      ])


def add_sponsor_to_set():
    """
    Add a sponsor to the set of sponsor information, even if it duplicates some info.
    :return:
    """
    sponsor_set.add((sponsor[0][FIELD_VAL].casefold().title(),      # Name
                     sponsor[1][FIELD_VAL].casefold().title(),      # Org
                     sponsor[2][FIELD_VAL].casefold().title(),      # Contact
                     sponsor[3][FIELD_VAL].casefold()))             # email


def empty_list(query_list: list) -> bool:
    """
    Determine if a list (e.g., drug) has no data. Sometimes trials have no drug at all listed,
    in other cases, the IMP section may have an entry without an drug-identifing information.
    :param query_list:
    :return: True if the list has no data in its third element.
    """
    for i in range(len(query_list)):
        if query_list[i][FIELD_VAL] != "":
            return False
    return True


def update_databases(filespec):
    """
    Calls subroutines to write data to each table of database.
    :return:
    """
    # Add uncommitted items to their respective lists
    with sqlite3.connect(filespec) as conn:
        if not empty_list(drug):
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
        - 1: database type (str)
        - 2: value (str)
        - 3: compiled regular expression (regexp object)
    :return: The captured substring
    """
    m = test_list[REGEXP_REF].match(" ".join(current_line.split()))
    if m:
        return m.group(1)
    else:
        return ""


def table_match(current_line: str, test_table: list, idx: int) -> bool:
    """
    Reads a line from the trial listing and tries to match it against
    regular expressions that define trial elements that are unique to each trial.
    When a match is found, the value is captured and stored back in the list.
    Caveat: Where the database is not consistent, this value may not be reliable.
    This algorithm favours responses with some content over null responses and for
    yes/no fields, will take a yes over a no.
    :param current_line: A line from the text listing of trials
    :param test_table: For each table in database, a list of:
        - 0: database header term (str)
        - 1: database type
        - 2: value (str)
        - 3: compiled regular expression (regexp object)
    :param idx: starting from what index in the table?
    :return:
    """
    for i in range(idx, len(test_table)):
        # Don't override previously defined data elements except a "yes"
        # trumps a "no" reply
        if test_table[i][FIELD_VAL].casefold() == "no":
            lm = list_match(current_line, test_table[i])
            if lm.casefold() == "yes":
                test_table[i][FIELD_VAL] = "yes"
                return True
        elif test_table[i][FIELD_VAL] == "":
            lm = list_match(current_line, test_table[i])
            if lm:
                test_table[i][FIELD_VAL] = lm
                return True
    return False


def banner(banchar="*", width=80) -> str:
    """ Print a line of some character to break up output"""
    return banchar * width


def parse_listing(infile: str, outfile: str):
    with open(infile, "r") as eu_trials:
        line = eu_trials.readline()
        while line:
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
            tested_term = imp_no_re.match(" ".join(line.split()))
            if tested_term:
                if not empty_list(drug):
                    add_drug_to_list()
                    wipe_list(drug, 0)
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
            # Finally, fill these tables
            if table_match(line, trial, 1) or table_match(line, drug, 0) or table_match(line, sponsor, 1):
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
trial_sponsor_protocol_re = re.compile("^A.4.1 Sponsor's protocol code number: (.*$)")
trial_isrctn_re = re.compile(r"^A.5.1 ISRCTN \(International Standard Randomised Controlled Trial\) number: (.*$)")
trial_who_utrn_re = re.compile(r"^A.5.3 WHO Universal Trial Reference Number \(UTRN\): (.*$)")
trial_NCT_re = re.compile(r"^A.5.2 US NCT \(ClinicalTrials.gov registry\) number: (NCT\d+)")
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
trial_n_re = re.compile("^F.4.2.2 In the whole clinical trial: (.*$)")
trial_network_name_re = re.compile("^G.4.1 Name of Organisation: (.*$)")
trial_end_of_trial_status_re = re.compile("^P. End of Trial Status: (.*$)")
trial_end_of_trial_date_re = re.compile("^P. Date of the global end of the trial: (.*$)")

# Compile regexps related to trial IMP(s)
imp_no_re = re.compile(r"D.IMP: \d+")  # do not capture - IMP numbering varies between MS records
imp_trade_name_re = re.compile("^D.2.1.1.1 Trade name: (.*$)")
imp_name_re = re.compile("^D.3.1 Product name: (.*$)")
imp_code_re = re.compile("^D.3.2 Product code: (.*$)")

# Compile regexps related to trial sponsor
sponsor_name_re = re.compile("^B.1.1 Name of Sponsor: (.*$)")
sponsor_org_re = re.compile("^B.5.1 Name of organisation: (.*$)")
sponsor_contact_re = re.compile("^B.5.2 Functional name of contact point: (.*$)")
sponsor_email_re = re.compile(r"^B.5.6 E-mail:\s*(\S+@\S+[.]\S+)\s*$")

# Compile regexps related to trial location
location_re = re.compile(r"^National Competent Authority:\s+(\S*)\s+[-]")
location_list_start_re = re.compile("^E.8.6.3 If E.8.6.1 or E.8.6.2 are Yes")
location_list_end_re = re.compile("^E.8.7 Trial has a data monitoring committee")
location_list_other_start_re = re.compile("^E.8.6.3 Specify the countries outside of the EEA")
location_list_other_end_re = re.compile("^E.8.7 Trial has a data monitoring committee:")

# List of unique elements to extract to the Trial table for each trial
trial = [["eudract", "TEXT NOT NULL PRIMARY KEY", "", trial_eudract_re],
         ["sponsor_code", "TEXT NOT NULL", "", trial_sponsor_code_re],
         ["status", "TEXT NOT NULL", "", trial_status_re],
         ["db_date", "TEXT NOT NULL", "", trial_db_date_re],
         ["title", "TEXT NOT NULL", "", trial_title_re],
         ["sponsor_protocol", "TEXT NOT NULL", "", trial_sponsor_protocol_re],
         ["isrctn", "TEXT NOT NULL", "", trial_isrctn_re],
         ["who_utrn", "TEXT NOT NULL", "", trial_who_utrn_re],
         ["nct", "TEXT NOT NULL", "", trial_NCT_re],
         ["placebo", "INTEGER NOT NULL", "", trial_placebo_re],
         ["condition", "TEXT NOT NULL", "", trial_condition_re],
         ["meddra_version", "TEXT NOT NULL", "", trial_MedDRA_version_re],
         ["meddra_level", "TEXT NOT NULL", "", trial_MedDRA_level_re],
         ["meddra_classification", "TEXT NOT NULL", "", trial_MedDRA_classification_re],
         ["meddra_term", "TEXT NOT NULL", "", trial_MedDRA_term_re],
         ["meddra_soc", "TEXT NOT NULL", "", trial_MedDRA_SOC_re],
         ["rare", "INTEGER NOT NULL", "", trial_rare_re],
         ["fih", "INTEGER NOT NULL", "", trial_fih_re],
         ["bioequivalence", "INTEGER NOT NULL", "", trial_bioequivalence_re],
         ["phase1", "INTEGER NOT NULL", "", trial_phase1_re],
         ["phase2", "INTEGER NOT NULL", "", trial_phase2_re],
         ["phase3", "INTEGER NOT NULL", "", trial_phase3_re],
         ["phase4", "INTEGER NOT NULL", "", trial_phase4_re],
         ["diagnosis", "INTEGER NOT NULL", "", trial_scope_diagnosis_re],
         ["prophylaxis", "INTEGER NOT NULL", "", trial_scope_prophylaxis_re],
         ["therapy", "INTEGER NOT NULL", "", trial_scope_therapy_re],
         ["safety", "INTEGER NOT NULL", "", trial_scope_safety_re],
         ["efficacy", "INTEGER NOT NULL", "", trial_scope_efficacy_re],
         ["pk", "INTEGER NOT NULL", "", trial_scope_PK_re],
         ["pd", "INTEGER NOT NULL", "", trial_scope_PD_re],
         ["randomised", "INTEGER NOT NULL", "", trial_scope_randomised_re],
         ["open_design", "INTEGER NOT NULL", "", trial_scope_open_re],
         ["single_blind", "INTEGER NOT NULL", "", trial_scope_single_blind_re],
         ["double_blind", "INTEGER NOT NULL", "", trial_scope_double_blind_re],
         ["crossover", "INTEGER NOT NULL", "", trial_scope_crossover_re],
         ["age_in_utero", "INTEGER NOT NULL", "", trial_age_in_utero_re],
         ["age_preterm", "INTEGER NOT NULL", "", trial_age_preterm_re],
         ["age_newborn", "INTEGER NOT NULL", "", trial_age_newborn_re],
         ["age_under2", "INTEGER NOT NULL", "", trial_age_under2_re],
         ["age_2to11", "INTEGER NOT NULL", "", trial_age_2to11_re],
         ["age12to17", "INTEGER NOT NULL", "", trial_age_12to17_re],
         ["age18to64", "INTEGER NOT NULL", "", trial_age_18to64_re],
         ["age_65plus", "INTEGER NOT NULL", "", trial_age_65plus_re],
         ["female", "INTEGER NOT NULL", "", trial_female_re],
         ["male", "INTEGER NOT NULL", "", trial_male_re],
         ["n", "TEXT NOT NULL", "", trial_n_re],
         ["network", "TEXT NOT NULL", "", trial_network_name_re],
         ["eot_date", "TEXT NOT NULL", "", trial_end_of_trial_date_re]]

# List of unique elements to extract to the Drug table for each trial
drug = [["trade", "TEXT NOT NULL", "", imp_trade_name_re],
        ["product", "TEXT NOT NULL", "", imp_name_re],
        ["code", "TEXT NOT NULL", "", imp_code_re]]

# List of unique elements to extract to the Sponsor table for each trial
sponsor = [["name", "TEXT NOT NULL", "", sponsor_name_re],
           ["org", "TEXT NOT NULL", "", sponsor_org_re],
           ["contact", "TEXT NOT NULL", "", sponsor_contact_re],
           ["email", "TEXT NOT NULL", "", sponsor_email_re]]

# Sets are used for sponsor and location to consolidate repeating data
drug_list = []
sponsor_set = set()
location_set = set()

source_file = "test2000x.txt"
database_name = input("Name of database to write? > ")
start_time = time.time()
create_databases(database_name)
parse_listing(source_file, database_name)
print("Run time: {}".format(time.time() - start_time))
