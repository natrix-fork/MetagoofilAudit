import re
import json
from typing import List
import requests
import textract
from textract.exceptions import ShellError
from bs4 import BeautifulSoup

from config import (creds, email_pattern,
                    phone_number_patterns, technology_pattern)


class GoogleCustomSearch:

    def __init__(self, file_types: List, site: str, usernames, index: int = 1, max_files=30):
        self.file_types = file_types
        self.site = site
        self.index = index
        self.files = []
        self.max_files = max_files
        self.limit_reached = False
        self.credentials = creds
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/48.0.2564.116 Safari/537.36'}
        self.usernames = usernames

    def grab_links(self):
        for file_type in self.file_types:
            if len(self.files) < self.max_files:
                self.get_specific_file_type_links(file_type)

    def get_specific_file_type_links(self, file_type, index=1):
        start_index = index
        api_response = False
        for i in range(0, len(self.credentials), 1):
            params = {
                'key': self.credentials[i]['google_cse_key'],
                'cx': self.credentials[i]['google_cse_cx'],
                'q': 'filetype:{0} site:{1}'.format(file_type, self.site),
                'start': start_index
            }
            api_response = requests.get(self.credentials[i]['api_url'], params=params, headers=self.headers)
            if api_response.status_code == 200:
                api_response = api_response.json()
                print('[+] Successfully retrieved data via credentials № {0}'.format(i + 1))
                break
            elif api_response.status_code != 200:
                if api_response.status_code == 403:
                    print('[-] Couldn"t retrieve data from google custom search via credentials № {0}'.format(i + 1))
                else:
                    print('[-] An error occurred while retrieving data from api. Status code: {0}'.format(
                        api_response.status_code))
                if i == len(self.credentials) - 1:
                    exit('[-] Requests on all accounts are exhausted!')
        if 'items' in api_response:
            if not self.limit_reached:
                for item in api_response['items']:
                    if len(self.files) == self.max_files:
                        print('[!] The number of files reached the specified maximum. Turning to file processing.')
                        self.limit_reached = True
                        break
                    self.files.append({
                        'type': file_type,
                        'link': item['link'],
                        'emails': [],
                        'usernames': [],
                        'phone_numbers': [],
                        'technologies': []
                    })
                    print('[+] Found {0} on {1}'.format(item['link'], self.site))
        if 'queries' in api_response and not self.limit_reached:
            if 'nextPage' in api_response['queries']:
                next_page_start_index = api_response['queries']['nextPage'][0]['startIndex']
                self.get_specific_file_type_links(file_type, index=next_page_start_index)

    def extract_useful_data(self, text):
        words = text.split()
        usernames = []
        emails = []
        phone_numbers = []
        technologies = []

        for pattern in phone_number_patterns:
            phone_numbers = list(set(phone_numbers + re.findall(pattern, text)))
        for word in words:
            is_valid = bool(re.match(email_pattern, word))
            if is_valid:
                emails.append(word)
            if word in self.usernames:
                usernames.append(word)
            elif re.match(technology_pattern, word):
                technologies.append(word)

        technologies = [{'technology': technology} for technology in set(technologies)]
        usernames = [{'username': username} for username in set(usernames)]
        emails = [{'email': email} for email in set(emails)]
        phone_numbers = [{'phone_number': phone_number} for phone_number in set(phone_numbers)]
        return emails, usernames, phone_numbers, technologies

    def parse_pdf(self, file):
        res = requests.get(file['link']).content
        with open('temp.pdf', 'wb') as f:
            f.write(res)
        try:
            text = textract.process('temp.pdf').decode('utf-8')
            emails, usernames, phone_numbers, technologies = self.extract_useful_data(text)
            file['emails'] = emails
            file['usernames'] = usernames
            file['phone_numbers'] = phone_numbers
            file['technologies'] = technologies
            self.print_file_processing(file)
        except ShellError:
            print('[-] There are illegal characters in {0}. Cannot parse data.'.format(file['link']))

    def parse_txt(self, file):
        res = requests.get(file['link']).text
        with open('temp.txt', 'w') as f:
            f.write(res)
        emails, usernames, phone_numbers, technologies = self.extract_useful_data(res)
        file['emails'] = emails
        file['usernames'] = usernames
        file['phone_numbers'] = phone_numbers
        file['technologies'] = technologies
        self.print_file_processing(file)

    def parse_md(self, file):
        res = requests.get(file['link']).text
        if file['link'].startswith('https://github.com/'):
            res = requests.get(file['link'] + '?raw=True').text
            if 'DOCTYPE' in res:
                self.files.remove(file)
                soup = BeautifulSoup(res, 'html.parser')
                links = soup.findAll('a', {'title': True, 'href': True})
                files = []
                for link in links:
                    if '.md' in link['title'] and link['title'] == link['href'].split('/')[-1]:
                        file_url = 'https://github.com/' + link['href'] + '?raw=True'
                        res = requests.get(file_url).text
                        emails, usernames, phone_numbers, technologies = self.extract_useful_data(res)
                        files.append({
                            'type': 'md',
                            'link': file_url,
                            'emails': emails,
                            'usernames': usernames,
                            'phone_numbers': phone_numbers,
                            'technologies': technologies
                        })
        else:
            emails, usernames, phone_numbers, technologies = self.extract_useful_data(res)
            file['emails'] = emails
            file['usernames'] = usernames
            file['phone_numbers'] = phone_numbers
            file['technologies'] = technologies
            self.print_file_processing(file)

    def grab_data(self):
        for file in self.files:
            if file['type'] == 'pdf':
                self.parse_pdf(file)
            elif file['type'] == 'md':
                self.parse_md(file)

    def save_data(self):
        with open('result.json', 'w') as f:
            json.dump(self.files, f)
        print('[!] Results saved to result.json.')

    @staticmethod
    def print_file_processing(file):
        print('File {0} processed. Reporting stats...'.format(file['link']))
        for key in file:
            if type(file[key]) == list:
                if file[key]:
                    print('\t [+] {0}:'.format(key.capitalize().replace('_', ' ')))
                    for item in file[key]:
                        for sub_key in item:
                            print('\t\t[+]{0}'.format(item[sub_key]))
                else:
                    print('[-] No {0} was found in {1}.'.format(key.replace('_', ' '), file['link']))
        print('__________________________________________________________________________________')
