# Eurovision
Extract the EU Clinical Trials registry into a database for analysis 

## Rationale
The intent of this project is to make information in the [EU Clinical Trial Registry](https://www.clinicaltrialsregister.eu/) (EUCTReg) accessible for analysis. The problem is that although the EUCTReg is online and searchable, it was established to provide a way to make clinical trial regulatory information transparently available, but deliberately designed to output data in way that does not facilitate research. This is a shame since other clinical trial registries such as [ClinicalTrials.gov](https://clinicaltrials.gov/) provide a wealth of useful information for researchers involved with clinical trials, but only a fraction of trials conducted in the European Union are replicated in other registries.

## Project Outline
The first step was to develop a python script ([scrape.py](https://github.com/dhakajack/Eurovision/blob/master/scrape.py)) to download the full text content of the registry. That is working, but rather than have everyone run it and potentially burden the EUCTReg website with large data requests, my plan is to run the script periodically and upload to a public repository. This text file is about 2 GB in size, so the next step is the [scan.py](https://github.com/dhakajack/Eurovision/blob/master/scan.py) script, which parses the text file and stores the result in an sqlite database (for now, eventually, a Postgres database). I did not attempt to extract every data element in the registry, but the script was written with modification in mind. Finally, the [toexcel.py](https://github.com/dhakajack/Eurovision/blob/master/toexcel.py) script provides a very rudimentary search facility and outputs the selected data set as an excel spreadsheet. The future plan is to make a web front-end to facilitate searching and provide both on-screen display and downloads of search results. Getting to that point could take a while. For now, I suggest taking advantage of what is already available, the dump of the full text contents of the website, the corresponding sqlite database or excel spreadsheet that includes all registry entries. This is a work in progress, so expect formats and features to shift as the process is refined. I should mention that I am not at all experienced when it comes to python, so suggestions are welcome.

## Details
### Origin
The EU Clinical Trials Registry is a public-facing portal that makes available non-confidential information stored in the EudraCT (European Union Drug Regulating Authorities Clinical Trials) database, which was established under the provisions of the EU clinical trial directive of 2001. That directive went into force in 2004, and since that time, when sponsors submit clinical trial applications EU member states competent authorities (CAs, i.e., regulatory agencies), the information goes into the EudraCT database, which is maintained by the European Medicines Agency (EMA). The database does not include all kinds of clinical trials -- its remit is limited to those that involve a medicinal product for human use and that involve at least one EU member state. Consequently, the registry does not list trials that focus solely on surgical procedures, medical devices or psychotherapeutic procedures. Additionally, the registry does not list trials that are phase I only (phase I/II are listed). Some pediatric studies completed prior to 2007 are listed on  another part of the registry website and since they follow a different format, they are not part of this project. Pediatric studies after that point are listed in the registry.

### Limitations
The EMA does not offer any API or web services to external parties to extract data from the registry; the only interface is a web form that is intended to be used manually. Aside from on-screen display in HTML, the only export format is plain text. Clinical trial applications (CTAs) are submitted to EU memberstate competent authorities as an XML document, and these roots are apparent in the format of the plain text document that follows the same outline, but unfortunately, without the formal tag structure. 

A major complicating factor is that a given trial, represented by a unique Eudract number, appears multiple times in the listing because sponsors were required to submit versions of the application to each EU member state involved. This allowed for certain items to vary across jurisdictions and for some items to be entered in the local language. However, it is also a huge source of error as the process involved manual data entry and not much data validation. Different versions of the CTA for the same trial are difficult to align because data are often variable (spelling, spacing, punctuation, language), appear in different order, represent different times in the trial, and are sometimes contradictory. The process has apparently improved over time and more recent records have better data quality.

The 2014 Clinical Trial regulation has not entered into force (at this time this is written), but it is likely that it will further improve data quality as sponsors will submit a CTA to single competent authority. It is not clear whether the new regulation will result in other structural changes in the registry.


