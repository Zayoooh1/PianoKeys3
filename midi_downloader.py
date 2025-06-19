import sys
import os
import requests
import urllib.parse
from bs4 import BeautifulSoup

def sanitize_filename(name_str):
    """Sanitizes a string to be a valid filename."""
    name_str = name_str.strip().replace(' ', '_')
    valid_chars = "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    sanitized_name = "".join(c if c in valid_chars else '_' for c in name_str)
    if not sanitized_name or sanitized_name.strip("._") == "":
        sanitized_name = "downloaded_midi"
    return sanitized_name[:100]

def download_and_save_file(midi_url_str, http_headers, original_song_title_str):
    """
    Downloads content from midi_url_str and saves it as a .mid file.
    Uses original_song_title_str to generate a filename.
    """
    try:
        print(f"Downloading MIDI from: {midi_url_str}")
        midi_response = requests.get(midi_url_str, headers=http_headers, stream=True, timeout=20)
        midi_response.raise_for_status()

        base_filename = sanitize_filename(original_song_title_str)
        filename = f"{base_filename}.mid"

        with open(filename, 'wb') as f:
            for chunk in midi_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Successfully downloaded and saved MIDI as: {os.path.abspath(filename)}")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error downloading MIDI {midi_url_str}: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error downloading MIDI {midi_url_str}: {req_err}")
    except IOError as io_err:
        print(f"File error saving MIDI: {io_err}")
    except Exception as e:
        print(f"An unexpected error occurred during download/save: {e}")

def find_and_download_midi_on_song_page(song_page_url_str, http_headers, original_song_title):
    """
    Accesses the individual song page, finds the MIDI download link, and initiates download.
    """
    try:
        print(f"Accessing song page: {song_page_url_str}")
        song_page_response = requests.get(song_page_url_str, headers=http_headers, timeout=10)
        song_page_response.raise_for_status()

        song_soup = BeautifulSoup(song_page_response.text, 'html.parser')

        midi_download_url = None

        all_links_on_song_page = song_soup.find_all('a', href=True)
        for link_tag in all_links_on_song_page:
            href_value = link_tag['href']
            if href_value.lower().endswith('.mid'):
                midi_download_url = href_value
                break

        if not midi_download_url:
            possible_download_texts = ["download midi", "download .mid", "get midi"]
            for link_tag in all_links_on_song_page:
                link_text_lower = link_tag.text.lower()
                if any(text in link_text_lower for text in possible_download_texts):
                    midi_download_url = link_tag['href']
                    break

        if not midi_download_url:
            dl_button = song_soup.find('a', id='downloadLink') or \
                        song_soup.find('a', class_='btn-download-midi') or \
                        song_soup.find('input', type='submit', value='Download')
            if dl_button and dl_button.get('href'):
                 midi_download_url = dl_button['href']

        if midi_download_url:
            midi_download_url = urllib.parse.urljoin(song_page_url_str, midi_download_url)
            print(f"Found MIDI download link: {midi_download_url}")
            download_and_save_file(midi_download_url, http_headers, original_song_title)
        else:
            print(f"Could not find a MIDI download link on page: {song_page_url_str}")

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error accessing song page {song_page_url_str}: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Error accessing song page {song_page_url_str}: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred on song page {song_page_url_str}: {e}")

def download_midi_from_freemidi(song_title_str):
    print(f"Searching for MIDI: {song_title_str}")

    search_query = urllib.parse.quote_plus(song_title_str)
    search_url = f"https://freemidi.org/search?query={search_query}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Fetching search results from: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        print("Parsing search results...")
        soup = BeautifulSoup(response.text, 'html.parser')

        song_page_url = None
        found_link_tag = None

        results_divs = [
            soup.find('div', class_='results-list'),
            soup.find('div', class_='search-results'),
            soup.find('div', id='results'),
            soup.find('table', class_='resultsTable')
        ]

        for container in results_divs:
            if container:
                links_in_container = container.find_all('a', href=True)
                for link in links_in_container:
                    if song_title_str.lower().split() and \
                       song_title_str.lower().split()[0] in link.text.lower():
                        found_link_tag = link
                        break
                if found_link_tag:
                    break

        if not found_link_tag:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                if song_title_str.lower() in link.text.lower():
                    href = link['href']
                    if not any(x in href for x in ['/genre-', '/artist-', 'javascript:', '#']):
                        found_link_tag = link
                        break

        if found_link_tag:
            relative_url = found_link_tag['href']
            song_page_url = urllib.parse.urljoin(search_url, relative_url)
            print(f"Found potential song page link: {song_page_url}")
            find_and_download_midi_on_song_page(song_page_url, headers, song_title_str)
        else:
            print(f"No song page link found for '{song_title_str}' in search results.")
            return

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Status code: {response.status_code if 'response' in locals() and hasattr(response, 'status_code') else 'N/A'}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the request: {req_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python midi_downloader.py "<song_title>"")
        sys.exit(1)

    song_title_arg = sys.argv[1]
    download_midi_from_freemidi(song_title_arg)

if __name__ == '__main__':
    main()
