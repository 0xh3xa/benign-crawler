import os
import re
import time
import urllib.parse
import uuid

import requests
from bs4 import BeautifulSoup

# Define the base URL
base_url = 'https://filehippo.com/popular/'
# base_url = 'https://filehippo.com/search/?q=portable'

# Create a folder to save downloaded files
download_folder = 'downloads'
os.makedirs(download_folder, exist_ok=True)


def get_soup(url):
    response = requests.get(url)
    response.raise_for_status()  # Check for request errors
    return BeautifulSoup(response.text, 'html.parser')


def extract_download_links(soup):
    download_links = []
    for link in soup.find_all('a', class_='card-program'):
        download_page_url = link['href']
        download_page_soup = get_soup(download_page_url)

        # Try to find the direct download button
        download_button = download_page_soup.find('a',
                                                  class_='program-button program-button--download program-actions-header__button program-button-download js-program-button-download')
        if download_button and 'href' in download_button.attrs:
            download_links.append((download_button['href'], link.text.strip()))

    return download_links


def decode_content_disposition(content_disposition):
    # Find the filename in the content-disposition header
    filename = re.findall('filename\*=([^;]+)', content_disposition)
    if filename:
        filename = urllib.parse.unquote(filename[0].split("''")[1])
    else:
        filename = re.findall('filename=([^;]+)', content_disposition)
        if filename:
            filename = filename[0].strip('"')
        else:
            filename = None
    return filename


def download_file(url, default_file_name, retry_delay=2):
    while True:
        try:
            response = requests.head(url)
            response.raise_for_status()

            # Check if the file size is greater than 200 MB
            file_size = int(response.headers.get('Content-Length', 0))
            if file_size > 500 * 1024 * 1024:  # 200 MB
                print(f'Skipping {default_file_name} as it is larger than 200 MB')
                break

            response = requests.get(url, stream=True)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            print(content_type)
            if 'text/html' in content_type:
                download_page_soup = get_soup(url)
                script_tag = download_page_soup.find('script', attrs={'data-qa-download-url': True})
                if script_tag and 'data-qa-download-url' in script_tag.attrs:
                    url = script_tag['data-qa-download-url']
                    response = requests.get(url, stream=True)

            file_name = default_file_name
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                file_name = decode_content_disposition(content_disposition)
            else:
                file_extension = '.zip' if 'zip' in url else '.exe'
                if file_extension == '.zip':
                    print(f'Skipping zip file from {url}')
                    break

            if file_name and file_name == 'file':
                file_name = file_name + str(uuid.uuid4()) + ".zip"
            file_path = os.path.join(download_folder, file_name)
            print(f'Downloading from: {url}')
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f'Downloaded: {file_name}')
            break
        except Exception as e:
            print(f'Unable to download from {url}, error {e}')
            break


def scrape_and_download(base_url):
    page_number = 1
    while True:
        current_url = f'{base_url}{page_number}/'
        # current_url = f'{base_url}?p={page_number}/'
        print(f'Scraping page: {current_url}')
        soup = get_soup(current_url)
        download_links = extract_download_links(soup)
        if not download_links:
            print('No more download links found, stopping.')
            break
        for download_link, file_name in download_links:
            download_file(download_link, file_name)
        page_number += 1
        time.sleep(10)


print('Starting download process...')
scrape_and_download(base_url)
print('All downloads completed.')
