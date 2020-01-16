import re
import json
from typing import List
import requests
import textract
from bs4 import BeautifulSoup

from validate_email import validate_email

from config import (google_cse_cx, google_cse_key,
                    api_url)


class GoogleCustomSearch:

    def __init__(self, file_types: List, site: str, index: int = 1, max_files=30):
        self.file_types = file_types
        self.site = site
        self.index = index
        self.files = []
        self.max_files = max_files
        self.credentials = [{
            'google_cse_cx': google_cse_cx,
            'google_cse_key': google_cse_key
        }]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/48.0.2564.116 Safari/537.36'}
        self.PHONE_NUMBER_PATTERN = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'

        try:
            with open('usernames.txt', 'r') as f:
                self.USERNAMES = f.read().splitlines()
        except FileNotFoundError:
            self.USERNAMES = []

    def grab_links(self):
        for file_type in self.file_types:
            if len(self.files) < self.max_files:
                self.get_specific_file_type_links(file_type)

    def get_specific_file_type_links(self, file_type, index=1):
        start_index = index
        params = {
            'key': google_cse_key,
            'cx': google_cse_cx,
            'q': 'filetype:{0} site:{1}'.format(file_type, self.site),
            'start': start_index
        }
        api_response = requests.get(api_url, params=params, headers=self.headers).json()
        if 'items' in api_response:
            for item in api_response['items']:
                if len(self.files) == self.max_files:
                    break
                self.files.append({
                    'type': file_type,
                    'link': item['link'],
                    'emails': [],
                    'usernames': [],
                })
        if 'queries' in api_response:
            if 'nextPage' in api_response['queries']:
                next_page_start_index = api_response['queries']['nextPage'][0]['startIndex']
                self.get_specific_file_type_links(file_type, index=next_page_start_index)

    def extract_useful_data(self, text):
        words = text.split()
        usernames = []
        emails = []
        phone_numbers = [number for number in re.findall(self.PHONE_NUMBER_PATTERN, text)]
        for word in words:
            is_valid = validate_email(word)
            if is_valid:
                emails.append(word)
            if word in self.USERNAMES:
                usernames.append(word)
        emails = [{'email': email} for email in set(emails)]
        phone_numbers = [{'phone_number': phone_number} for phone_number in set(phone_numbers)]
        return emails, usernames, phone_numbers

    def parse_pdf(self, file):
        res = requests.get(file['link']).content
        with open('temp.pdf', 'wb') as f:
            f.write(res)
        text = textract.process('temp.pdf').decode('utf-8')
        emails, usernames, phone_numbers = self.extract_useful_data(text)
        file['emails'] = emails
        file['usernames'] = usernames
        file['phone_numbers'] = phone_numbers

    def parse_txt(self, file):
        res = requests.get(file['link']).text
        with open('temp.txt', 'w') as f:
            f.write(res)
        emails, usernames, phone_numbers = self.extract_useful_data(res)
        file['emails'] = emails
        file['usernames'] = usernames
        file['phone_numbers'] = phone_numbers

    def parse_md(self, file):
        res = requests.get(file['link']).text
        if file['link'].startswith('https://github.com/'):
            res = requests.get(file['link']+'?raw=True').text
            if 'DOCTYPE' in res:
                soup = BeautifulSoup(res)
                links = soup.findAll('a')
                for link in links:
                    if '.md' in link['title']:
                        res = requests.get(file['link']+'/'+link['title']+'?raw=True').text
                        break
        emails, usernames, phone_numbers = self.extract_useful_data(res)
        file['emails'] = emails
        file['usernames'] = usernames
        file['phone_numbers'] = phone_numbers

    def grab_data(self):
        for file in self.files:
            if file['type'] == 'pdf':
                self.parse_pdf(file)
            elif file['type'] == 'md':
                self.parse_md(file)

    def save_data(self):
        with open('result.json', 'w') as f:
            json.dump(self.files, f)
