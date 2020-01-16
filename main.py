import argparse
from scraper import GoogleCustomSearch
#
# parser = argparse.ArgumentParser(description='Metagoofil - Search and download specific filtypes')
# parser.add_argument('-d', dest='domain', action='store', required=True, help='Domain to search.')
# parser.add_argument('-l', dest='search_max', action='store', type=int, default=100,
#                     help='Maximum results to search.  DEFAULT: ALL')
# parser.add_argument('-n', dest='download_file_limit', default=100, action='store', type=int,
#                     help='Maximum number of files to download per filetype.  DEFAULT: 100')
# args = parser.parse_args()

finder = GoogleCustomSearch(['md'], 'github.com', 1)
finder.grab_links()
finder.grab_data()
finder.save_data()