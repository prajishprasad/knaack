# This script scrapes the NAAC accreditation status universities from the NAAC website.
import requests
from bs4 import BeautifulSoup
import time
import os
MAIN_URL = "https://assessmentonline.naac.gov.in/public/index.php/hei_dashboard"
GRADE_SHEET_FOLDER = "Grade_Sheet_Report"
IIQA_FOLDER = "IIQA_Report"
PEER_TEAM_REPORT_FOLDER = "Peer_Team_Report"
SSR_REPORT_FOLDER = "SSR_Report"

def scrape_from_naac_accreditation_website():
    """Scrape the NAAC table from the NAAC website and save it as a JSON file. As of 6/7/2025, there are 9119 entries in the table."""
    # Start a session to handle cookies
    session = requests.Session()

    # Step 1: GET the main page
    response = session.get(MAIN_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the CSRF token from the hidden input
    token = soup.find('input', {'name': '_token'})['value']
    print("Extracted token:", token)

    # Step 2: Send GET request with token in URL
    timestamp = int(time.time() * 1000)
    params = {
        "_token":token,
        "inst_type":"0",
        "state":"0",
        "cycle":"0",
        "iiqa_status":"5",
        "date_range":"",
        "inst_name":"",
        "draw":"1",
        "columns[0][data]":"hei_assessment_id",
        "columns[0][name]":"hei_assessment_id",
        "columns[0][searchable]":"false",
        "columns[0][orderable]":"true",
        "columns[0][search][value]":"",
        "columns[0][search][regex]":"false",
        "columns[1][data]":"hei_name",
        "columns[1][name]":"hei_basic_profile.hei_name",
        "columns[1][searchable]":"true",
        "columns[1][orderable]":"true",
        "columns[1][search][value]":"",
        "columns[1][search][regex]":"false",
        "columns[2][data]":"aishe_id",
        "columns[2][name]":"hei_basic_profile.aishe_id",
        "columns[2][searchable]":"true",
        "columns[2][orderable]":"true",
        "columns[2][search][value]":"",
        "columns[2][search][regex]":"false",
        "columns[3][data]":"other_address",
        "columns[3][name]":"other_address",
        "columns[3][searchable]":"false",
        "columns[3][orderable]":"true",
        "columns[3][search][value]":"",
        "columns[3][search][regex]":"false",
        "columns[4][data]":"state_name",
        "columns[4][name]":"state_name",
        "columns[4][searchable]":"false",
        "columns[4][orderable]":"true",
        "columns[4][search][value]":"",
        "columns[4][search][regex]":"false",
        "columns[5][data]":"iiqa_submitted_date",
        "columns[5][name]":"iiqa_submitted_date",
        "columns[5][searchable]":"false",
        "columns[5][orderable]":"true",
        "columns[5][search][value]":"",
        "columns[5][search][regex]":"false",
        "columns[6][data]":"date_of_decleration",
        "columns[6][name]":"date_of_decleration",
        "columns[6][searchable]":"false",
        "columns[6][orderable]":"true",
        "columns[6][search][value]":"",
        "columns[6][search][regex]":"false",
        "columns[7][data]":"grade",
        "columns[7][name]":"grade",
        "columns[7][searchable]":"false",
        "columns[7][orderable]":"true",
        "columns[7][search][value]":"",
        "columns[7][search][regex]":"false",
        "columns[8][data]":"edit_button",
        "columns[8][name]":"edit_button",
        "columns[8][searchable]":"false",
        "columns[8][orderable]":"false",
        "columns[8][search][value]":"",
        "columns[8][search][regex]":"false",
        "order[0][column]":"5",
        "order[0][dir]":"desc",
        "start":"0",
        "length":"9119",
        "search[value]":"",
        "search[regex]":"false",
        "_":"1751810503713"
    }

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": MAIN_URL,
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }   
    data_resp = session.get(MAIN_URL, params=params, headers=headers)

    ## Download this as a file
    with open('naac_accreditation_data_final_all.json', 'w', encoding='utf-8') as file:
        file.write(data_resp.text)
    #print(data_resp.text)

    return None

def download_reports_for_institution(hei_assessment_id, aishe_id):
    """Download the NAAC Peer Team Report and Grade Sheet for a given HEI Assessment ID"""
    base_url = f"{MAIN_URL}/{hei_assessment_id}"
    params = {
        "status": "5"
    }
    view_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": MAIN_URL,
        "Accept": "text/html, */*; q=0.01",
    }
    response = requests.get(base_url, params=params, headers=view_headers)
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    divs = soup.find_all("div", class_="col-md-3")

    for div in divs:
        links = div.find_all("a", href=True)
        #print(f"Found {len(links)} links in div: {div.text.strip()}")
        for link in links:
            #Download the report
            report_url = link["href"]
            report_response = requests.get(report_url)
            report_category = report_url.split("/")[-2]
            report_folder = ""
            
            if report_category == "peerteam_report":
                report_folder = PEER_TEAM_REPORT_FOLDER
            elif report_category == "iiqa_report":
                report_folder = IIQA_FOLDER
            elif report_category == "ssr_report":
                report_folder = SSR_REPORT_FOLDER
            else:
                report_folder = GRADE_SHEET_FOLDER
            
            report_filename = str(aishe_id) + "_"+  report_category+ ".pdf"
            #Navigate to the appropriate folder
            import os
            if not os.path.exists(report_folder):
                os.makedirs(report_folder)
            report_filename = os.path.join(report_folder, report_filename)
            #Download the report
            with open(report_filename, 'wb') as report_file:
                report_file.write(report_response.content)
            print(f"Downloaded: {report_filename}")

def check_report_already_exists(aishe_id):
    peer_report_folder = os.path.join(PEER_TEAM_REPORT_FOLDER)
    ssr_report_folder = os.path.join(SSR_REPORT_FOLDER)
    iiqa_report_folder = os.path.join(IIQA_FOLDER)
    grade_sheet_folder = os.path.join(GRADE_SHEET_FOLDER)
    if not os.path.exists(peer_report_folder):
        os.makedirs(peer_report_folder)
    if not os.path.exists(ssr_report_folder):
        os.makedirs(ssr_report_folder)
    if not os.path.exists(iiqa_report_folder):
        os.makedirs(iiqa_report_folder)
    if not os.path.exists(grade_sheet_folder):
        os.makedirs(grade_sheet_folder)
    peer_report_filename = os.path.join(peer_report_folder, str(aishe_id) + "_peerteam_report.pdf")
    ssr_report_filename = os.path.join(ssr_report_folder, str(aishe_id) + "_ssr_report.pdf")
    iiqa_report_filename = os.path.join(iiqa_report_folder, str(aishe_id) + "_iiqa_report.pdf")
    grade_sheet_filename = os.path.join(grade_sheet_folder, str(aishe_id) + "_grade_sheet_rpt.pdf")
    if os.path.exists(peer_report_filename) and os.path.exists(ssr_report_filename) and os.path.exists(iiqa_report_filename) and os.path.exists(grade_sheet_filename):
        return True
    return False

def download_naac_reports(naac_data_file):
    """Download the NAAC Peer Team Report and Grade Sheet from the json file"""
    #Read the JSON file
    import json
    with open(naac_data_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    for entry in data['data']:
        hei_assessment_id = entry['hei_assessment_id']
        aishe_id = entry['aishe_id']
        if check_report_already_exists(aishe_id):
            print(f"Report already exists for HEI Assessment ID: {hei_assessment_id}")
            continue
        print(f"Downloading reports for HEI Assessment ID: {hei_assessment_id}")
        download_reports_for_institution(hei_assessment_id=hei_assessment_id, aishe_id=aishe_id)
        #time.sleep(1)

if __name__ == "__main__":
    print("Starting script...")
    #Uncomment the following lines when you want to scrape the NAAC Website
    #scrape_naac_accreditation()
    #download_naac_reports(naac_data_file='naac_accreditation_data_final_all.json')