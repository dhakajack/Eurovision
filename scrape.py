"""
Download every trial publicly listed on the EU Clinical trial register,
page by page as a huge text file.
"""

import requests
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# To not have to deal with the SSL connection, certs, etc.
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

TOP_PAGE = 5  # one more than last page
URL = "https://www.clinicaltrialsregister.eu/ctr-search/rest/download/full?query=&page={}&mode=current_page"


def sleep_on_error(error_type: str, sleep_duration: int) -> int:
    print("{} Error. Resetting after {} seconds".format(error_type, sleep_duration))
    time.sleep(sleep_duration)
    if sleep_duration < 300:
        sleep_duration *= 2
    return sleep_duration


start_time = time.time()
filespec = time.strftime("%Y%m%d-%H%M")
print("Executing")
with open(filespec, "w") as test_file:
    for page_number in range(1, TOP_PAGE):
        print("Accessing page {}".format(page_number))
        print("### PAGE {} ####".format(page_number), file=test_file)
        read_again = True
        # noinspection PyRedeclaration
        sleep_time = 1
        while read_again:
            try:
                # timeout parameters: time to connect, time to begin reading response
                page = requests.get(URL.format(page_number), verify=False, timeout=(2, 5))
            except requests.exceptions.Timeout:
                sleep_time = sleep_on_error("Time Out", sleep_time)
            except requests.exceptions.ConnectionError:
                sleep_time = sleep_on_error("Connection", sleep_time)
            else:
                read_again = False
        print(page.text, file=test_file)
        # time.sleep(5) # The website does not complain about repeated hits, so no need to slow it down
print("Done. Elapsed time {0:.2f} minutes.".format((time.time() - start_time)/60))
