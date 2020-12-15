from bs4 import BeautifulSoup 
from fuzzywuzzy import fuzz
from pykakasi import kakasi
from collections import Counter, defaultdict

import requests
import pandas as pd
import re
import numpy as np
import discord
import utils

#################################################

# initialized settings for pykakasi module
kakasi = kakasi()
kakasi.setMode("H","a") # Hiragana to ascii, default: no conversion
kakasi.setMode("K","a") # Katakana to ascii, default: no conversion
kakasi.setMode("J","a") # Japanese to ascii, default: no conversion
kakasi.setMode("r","Hepburn") # default: use Hepburn Roman table
kakasi.setMode("s", True) # add space, default: no separator
kakasi.setMode("C", False) # capitalize, default: no capitalize
conv = kakasi.getConverter()

#################################################

class Song:
    def __init__(self, song, artist, bpm, key, links):
        self.song = song
        self.artist = artist
        self.bpm = bpm
        self.key = key
        self.links = {}

    def set_links(self, links_dict):
        self.links = links_dict

#################################################

def get_table(SOURCE):
    """
    Scrapes the main table from the ct2viewer website. 
    Used for grabbing song links since pd.html doesn't also scrape hyperlinks.
    
    :param SOURCE: ct2viewer site link
    :return: HTML table
    """

    try:
        r = requests.get(SOURCE)
        c2v = BeautifulSoup(r.content, features = 'lxml')
        table = c2v.body.table.tbody

        return table
    
    except:
        return Exception("Unable to request from page.")

def get_initial_df(SOURCE):
    """
    Reads all relevant information from the site to a dataframe.

    :param SOURCE: ct2viewer site link
    :return: pandas DataFrame object containing information such as song titles,
            artist names, DIFFICULTIES, BPMs and so on.
    """ 

    charts_df = pd.read_html(SOURCE, encoding = "UTF-8")
    charts_df = pd.concat(charts_df)
    charts_df.rename(columns = {"Lv.":"Diff_E","Lv..1":"Diff_H",
        "Lv..2":"Diff_C","Lv..3":"Diff_G"
        ,"Chart Page":"Chart_E","Chart Page.1":"Chart_H"
        ,"Chart Page.2":"Chart_C","Chart Page.3":"Chart_G"
        ,"Chart Page.4":"Chart_CR"}, inplace = True)

    charts_df = charts_df[charts_df['Song'].notna()]

    return charts_df

#################################################

def get_links_by_difficulty(table):
    """
    Formats all links from the HTML table obtained earlier and puts them
    into a dictionary.

    :param table: HTML table
    :return: Dictionary in the format: {<difficulty> : [list of <links>]}
    """

    links = [link.get('href') for link in table.find_all('a')]
    linksFormatted = [f"{link}.html" for link in links]

    return {
            diff: [link for link in linksFormatted if diff in link] 
                    for diff in utils.REGEXES_BY_DIFF.keys()
            }
    

def get_keys_by_difficulty(links_dict):
    """
    All songs from the site are formatted in this manner:
    https://ct2view.the-kitti.com/chartlist/<song identifier>/<difficulty>

    This function returns all unique song identifiers (keys) present for 
    each difficulty using the regexes from earlier.

    :param links_dict: Dictionary of links by difficulty
    :return: Dictionary in the format: {<difficulty> : [list of <keys>]}
    """

    keys_dict = dict()

    for diff, regex in utils.REGEXES_BY_DIFF.items():
        result = [" ".join(key.split("_")) for link in links_dict[diff] 
                        for key in regex.findall(link)]
        keys_dict[diff] = result

    return keys_dict

def merge_keys_and_links(table):
    """
    Helper function. Merges links_dict and keys_dict

    :param table: HTML table scraped from site
    :return: Dictionary of dictionaries in the format: 
            {<difficulty> : [list of dictionaries {<key> : <link>}]}
    """

    links_dict = get_links_by_difficulty(table)
    keys_dict = get_keys_by_difficulty(links_dict)
 
    return {k: dict(zip(keys_dict[k], links_dict[k])) for k in keys_dict}

#################################################

def merge_data(charts_df, merged_dict):
    """
    Create a new DataFrame object containing song keys to be merged with
    the original DataFrame.

    :param charts_df: Original DataFrame containing information about each
                      chart, excluding unique song keys.
    :param merged_dict: Dictionary of dictionaries previously obtained
                        containing DIFFICULTIES and their corresponding
                        keys/links.

    :return: New DataFrame now with each song's corresponding unique key. 
    """

    # all unique keys are present only for CHAOS difficulty since the site
    # does not include most EASY/HARD difficulty views
    links_df = pd.DataFrame({
                            'Song' : charts_df.Song, 
                            'Artist' : charts_df.Artist, 
                            'Key' : list(merged_dict['chaos.html'].keys()), 
                            })

    links_df.to_csv("links.csv")
    charts_df.to_csv("charts.csv")

    return pd.merge(
            left = charts_df, right = links_df, 
            left_on = ['Song', 'Artist'], 
            right_on = ['Song', 'Artist']
        )

def get_romanized_titles(merged_df):
    """
    Create new column in the DataFrame for ONLY Japanese-titled songs.
    This column contains the romanized title of the song obtained from pykakasi.

    :param merged_df: Merged DataFrame containing all relevant song info
    :return: Same DataFrame but now with romanized titles
    """
    for song in merged_df.Song:
        # if title is in japanese
        if utils.JP_REGEX.findall(song):
            # assign japanese title
            merged_df.loc[merged_df.Song == song, 'Key_J'] = conv.do(song)

        else: 
            # fill other rows with whitespace as opposed to NaN by default
            merged_df.loc[merged_df.Song == song, 'Key_J'] = ""

    return merged_df

def handle_duplicates(merged_df):
    """
    Pre-processing function to handle songs that have identical titles.
    :param merged_df: DataFrame containing all relevant song info
    :return: Same DataFrame but with duplicate song titles being in the
            format <Song> (<Artist>)
    """

    # if there are duplicates
    if merged_df.duplicated(subset = ['Song']).any():
        duplicated = merged_df.duplicated(subset = ['Song'])
        
        # get a list of these duplicates
        song_duplicates = list(merged_df[duplicated].to_records())
        
        for dupe in song_duplicates:
            # get index of each song with the same title
            indexes = merged_df.index[merged_df.Song == dupe.Song].tolist()

        # pandas doesn't allow assignment during iteration
        for index in indexes:
            # append the artist's name in brackets
            merged_df.loc[index, 'Song'] += f" ({merged_df.loc[index].Artist})"
            
    return merged_df

def get_merged_df(charts_df, merged_dict):
    """
    Helper function to obtain and perform all necessary preprocessing steps on 
    the merged DataFrame.

    :param charts_df: Original DataFrame containing information about each
                      chart, excluding unique song keys.
    :param merged_dict: Dictionary of dictionaries previously obtained
                        containing DIFFICULTIES and their corresponding
                        keys/links.
    :return: Final merged DataFrame containing unique keys, romanized keys 
            for songs with Japanese titles, and duplicates handled accordingly.
    """

    merged_df = merge_data(charts_df, merged_dict)
    merged_df = get_romanized_titles(merged_df)
    merged_df = handle_duplicates(merged_df)

    return merged_df

#################################################

def compare_fuzz(song, best_matches, best_fuzz_ratio, fuzz_value):
    """
    compare_fuzz: A helper function to compare fuzz values then add it to 
    the best_matches array, if needed
    :param song: The song to potentially add
    :param best_matches: A list of best matches
    :param best_fuzz_ratio: The currently best fuzz ratio
    :param fuzz_value: Fuzz ratio of the song compared to user's query
    :return: True if the fuzz_ratio was better and needs to be updated
             False if the fuzz_ratio does not need to be modified
    """

    # If fuzz_value is greater than best_fuzz ratio, set best to fuzz_value and set best_matches to only that song
    if fuzz_value > best_fuzz_ratio:
        best_matches.clear()
        best_matches.append(song)
        return True

    # Otherwise, if fuzz and best are equal, add the song to the list
    elif fuzz_value == best_fuzz_ratio:
        best_matches.append(song)
        return False

    return False


def search_song(df, query):
    """
    search_song: Fetches the closest matching song from the database
                    - If multiple are found, return a list of potential songs
    :param df: DataFrame object to obtain info of search result
    :param query: A query in string format, usually the name of a song
    :return: DataFrame object containing all information about the song
    """
    best_fuzz_ratio = 0
    best_matches = []

    # check if input is japanese
    is_japanese = re.search(JP_REGEX, query)
    
    for index, row in df.iterrows():
        # if there is an exact match simply return it
        if row.Song.lower() == query.lower():
                return df.loc[df.Song == row.Song]

        # check against the Song attribute regardless if input is in EN/JP
        fuzz_value = fuzz.token_set_ratio(row.Song, query)

        if compare_fuzz(row, best_matches, best_fuzz_ratio, fuzz_value):
            best_fuzz_ratio = fuzz_value
            
        if not is_japanese:
            # also check if input is romanized Japanese
            fuzz_value_romanized = fuzz.token_set_ratio(row.Key_J, query)
            
            if compare_fuzz(row, best_matches, best_fuzz_ratio, fuzz_value_romanized):
                best_fuzz_ratio = fuzz_value_romanized

    # if there are no good matches, return nothing
    if best_fuzz_ratio < 0.2:
        return []

    # removes duplicates from search
    songs = set([song.Song for song in best_matches])
    output = [df.loc[df.Song == song] for song in songs]

    return output


def search_difficulty(df, query):
    output = []

    for index, row in df.iterrows():
        if (row.Diff_E == query or row.Diff_H == query 
            or row.Diff_C == query or row.Diff_G == query):
            
            output.append(row.Song)

    partitioned_output = [output[i : i + 6] for i in range(0, len(output), 6)]
    print(partitioned_output)

    return partitioned_output

#################################################

def get_images(link):
    """
    Gets the song artwork and character logo from the link of a song.
    :param link: Link to scrape thumbnail from
    :return: Link to artwork and logo in proper format
    """

    r = requests.get(link)
    page = BeautifulSoup(r.content, features = 'lxml')
    images = page.find_all('img')

    # very hacky code based on the way the site's images are formatted.
    # not sure how to improve
    artwork = "".join(image['src'] for image in images if 'thumbnail' in image['src'])

    if (root := "../..") in artwork:
        artwork = artwork.replace(root, utils.PREFIX)
    else:
        artwork = utils.PREFIX + artwork

    return artwork

def embed_song(merged_dict, song):
    """
    Outputs details of a song including the song's title, its artist, BPM
    and hyperlinks to each of its (available) charts.
    :param merged_dict: Dictionary to find a chart's links
    :return: Formatted discord.Embed object
    """
    
    song = song.to_records()
    
    # obtain all available links to song
    links = [merged_dict[diff].get("".join(song.Key)) 
                for diff in utils.REGEXES_BY_DIFF.keys()]

    # since each song is guaranteed to have a CHAOS chart on the site
    # grab the thumbnail from the CHAOS link
    artwork = get_images(links[2])

    embed = discord.Embed(title = f'{"".join(song.Song)}', color = 0x1abc9c)
    embed.set_thumbnail(url = artwork)

    embed.add_field(name = "Artist", value = f'{"".join(song.Artist)}', inline = False)
    embed.add_field(name = "BPM", value = f'{"".join(song.BPM)}', inline = True)
    embed.add_field(name = "Character", value = f'{"".join(song.Character)}', inline = True)

    difficulty_string = handle_difficulty_string(song, links)

    embed.add_field(name = "Difficulty", value = difficulty_string, inline = False)
        
    return embed

def handle_difficulty_string(song, links):
    """
    Helper function. Returns a string that is formatted according to Discord's
    hyperlink syntax.
    :param song: song to return difficulty information of
    :param links: URL(s) containing links to view each difficulty's chart
    """
    difficulty_string = ""

    # obtain links and output in discord hyperlink format, i.e.
    # [text here](url here)
    if links[0] is not None:
        difficulty_string += f'[EASY {"".join(str(int(song.Diff_E)))}]({links[0]})'
        difficulty_string += " | "
    
    if links[1] is not None:
        difficulty_string += f'[HARD {"".join(str(int(song.Diff_H)))}]({links[1]})'
        difficulty_string += " | "
        
    difficulty_string +=  f'[CHAOS {"".join(str(int(song.Diff_C)))}]({links[2]})'

    if links[3] is not None:
        difficulty_string += " | "
        difficulty_string += f'[GLITCH {"".join(str(int(song.Diff_G)))}]({links[3]})'

    return difficulty_string

def process_search(merged_dict, search_result):
    """
    Helper function. Returns different outputs depending on the search result.
    :param merged_dict: Dictionary to obtain song links from
    :param search_result: Result of the function search_song
    :return: Appropriate discord.Embed object
    """
    print("search result")
    print(search_result)
    print(type(search_result))
    result = search_result.to_frame()
    print("post conversion")
    print(result)
    print(type(result))
    if len(result) == 0:
        return utils.generate_embed(
                    status = 'Error', 
                    msg =  """No songs found. There could be an error with
                                        your search or the bot."""
                )

    elif len(result) == 1:
        return embed_song(merged_dict, result)
        
    elif len(result) > 1:
        results = [row.Song for index, row in result.iterrows()]
        
        return utils.generate_embed(
                    status = 'Error',
                    msg = """Too many songs found. Please enter
                            a song from the list given.""" + "\r\n" 
                            + "\r\n".join(results)
                )