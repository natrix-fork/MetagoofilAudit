import argparse
from scraper import GoogleCustomSearch

parser = argparse.ArgumentParser(description='Metagoofil - Search and download specific filtypes')
parser.add_argument('-d', dest='domain', action='store', required=True, help='Domain to search.')
parser.add_argument('-n', dest='download_file_limit', default=30, action='store', type=int,
                    help='Maximum number of files to download.')
parser.add_argument('-u', dest='usernames_file', default='usernames.txt', type=str,
                    help='File name with usernames.')
parser.add_argument('-t', dest='types_file', default='types.txt', type=str,
                    help='File name with file types.')
args = parser.parse_args()

domain = args.domain
usernames_file = args.usernames_file
types_file = args.types_file

with open(usernames_file, 'r') as f:
    usernames = f.read().splitlines()

with open(types_file, 'r') as f:
    types = f.read().splitlines()

finder = GoogleCustomSearch(file_types=types, site=domain, usernames=usernames, index=1)
finder.grab_links()
finder.grab_data()
finder.save_data()
