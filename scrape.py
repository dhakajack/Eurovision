"""
Download every trial publicly listed on the EU Clinical trial register,
page by page as a huge text file. When this was written, that was the
only option available.
"""

import requests
import time
import urllib3
urllib3.disable_warnings()


URL = "https://www.clinicaltrialsregister.eu/ctr-search/rest/download/full?query=&page={}&mode=current_page"

print("Executing")
with open("full2002.txt", "w") as test_file:
    for page_number in range(0, 2004):
        print("Accessing page {}".format(page_number))
        print("###PAGE {} ####".format(page_number), file=test_file)
        page = requests.get(URL.format(page_number), verify=False)
        print(page.text, file=test_file)
        # time.sleep(5) # The website does not complain about repeated hits, so no need to slow it down
