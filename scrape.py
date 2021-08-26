"""
Download every trial publicly listed on the EU Clinical trial register,
page by page as a huge text file.
"""

import requests
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import re

# To not have to deal with the SSL connection, certs, etc.
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HOW_MANY_PAGES_URL = "https://www.clinicaltrialsregister.eu/ctr-search/search?query="
PAGES_URL = "https://www.clinicaltrialsregister.eu/ctr-search/rest/download/full?query=&page={}&mode=current_page"


def sleep_on_error(error_type: str, sleep_duration: int) -> int:
    print("{} Error. Resetting after {} seconds".format(error_type, sleep_duration))
    time.sleep(sleep_duration)
    if sleep_duration < 600:
        sleep_duration *= 2
    return sleep_duration


def access_page(url_string: str) -> requests.Response:
    sleep_time = 1
    read_again = True
    page = None
    while read_again:
        try:
            # timeout parameters: time to connect, time to begin reading response
            page = requests.get(url_string, verify=False, timeout=(2, 5))
        except requests.exceptions.Timeout:
            sleep_time = sleep_on_error("Time Out", sleep_time)
        except requests.exceptions.ConnectionError:
            sleep_time = sleep_on_error("Connection", sleep_time)
        else:
            if page.status_code != 200:
                sleep_on_error("Status {}".format(page.status_code), sleep_time)
            else:
                read_again = False
    return page


max_re = re.compile(r".*Displaying page 1 of ([0-9,]+).*")

top_page = 1
start_time = time.time()
filespec = time.strftime("%Y%m%d-%H%M")

print("Executing")

for line in access_page(HOW_MANY_PAGES_URL).text.splitlines():
    # print("*", line)
    m = max_re.match(line)
    if m:
        top_page = int("".join(m.group(1).split(","))) + 1
        print("Top Page is {}".format(top_page))
        break
if top_page == 1:
    raise Exception("Unable to determine last page of site to crawl.")

top_page = 5
with open(filespec, "w") as test_file:
    for page_number in range(1, top_page):
        print("Accessing page {}".format(page_number))
        print("### PAGE {} ####".format(page_number), file=test_file)
        print(access_page(PAGES_URL.format(page_number)).text, file=test_file)

print("Done. Elapsed time {0:.2f} minutes.".format((time.time() - start_time) / 60))
