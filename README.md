# Eurovision
Extract the EU Clinical Trials registry into a database for analysis 

## Rationale
The intent of this project is to make information in the EU Clinical Trial Registry (EUCTReg) accessible for analysis. The problem is that although the EUCTReg is online and searchable, it was established to provide a way to make clinical trial regulatory information transparently available, but deliberately designed to output data in way that does not facilitate research. This is a shame since other clinical trial registries such as ClinicalTrials.gov provide a wealth of useful information for researchers involved with clinical trials, but only a fraction of trials conducted in the European Union are replicated in other registries.

## Project Outline
The first step was to develop a python script (scrape.py) to download the full text content of the registry. That is working, but rather than have everyone run it and potentially burden the EUCTReg website with large data requests, my plan is to run the script periodically and upload to a public repository. This text file is about 2 GB in size, so the next step is the scan.py script, which parses the text file and stores the result in an sqlite database (for now, eventually, a Postgres database). I did not attempt to extract every data element in the registry, but the script was written with modification in mind. Finally, the toexcel.py script provides a very rudimentary search facility and outputs the selected data set as an excel spreadsheet. The future plan is to make a web front-end to facilitate searching and provide both on-screen display and downloads of search results. Getting to that point could take a while. For now, I suggest taking advantage of what is already available, the dump of the full text contents of the website, the corresponding sqlite database or excel spreadsheet that includes all registry entries. This is a work in progress, so expect formats and features to shift as the process is refined.

## Details
### 
