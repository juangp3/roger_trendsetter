#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : roger_main.py
@Date    : 10/31/19 11:43 PM
@Project : roger_trendsetter
@Author  : juangp3
"""
import unittest
from builtins import dict

import Algorithmia
import json
import nltk
from pathlib import Path

import requests
from requests.exceptions import HTTPError
import shutil

from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# system imports
from ibm_watson.natural_language_understanding_v1 import Features, KeywordsOptions
from googleapiclient.discovery import build
from wand.image import Image
from wand.drawing import Drawing
from wand.font import Font
from random import randrange


auth_key = {'algorithmia': {'apikey': 'simnbKMNi+ynZMGZJdKe8d2CjJu1'},
            'nlu_watson': {'apikey': 'dx9aHzStLwZRW6Ltkjb5nAJjju9iANxLqQQXy026jLV9',
                           'version': '2019-11-06',
                           'url': 'https://gateway-lon.watsonplatform.net/natural-language-understanding/api'},
            'Google': {'apikey': 'AIzaSyBQ0jKnW3SYaGJitVnNGtwULwwFnvUoS_I',
                       'searchEng': '012896964214635737899:9rpxasrajfj'}}

MODULE_PATH = Path.cwd()
RAW_DATA_PATH = MODULE_PATH.joinpath('raw')
IMAGES_DATA_PATH = MODULE_PATH.joinpath('images')


class searchTerm(object):

    def __init__(self):
        super(searchTerm, self).__init__()
        self.search_term = ''
        self.search_prefix = ''

    def ask_search_term(self):
        asking_message = 'Hi! What do you want me to look?\n'
        search_term = input(asking_message)

        return search_term

    def ask_search_prefix(self):
        search_prefix = ''
        prefix = ["Who is", "What is", "The history of"]
        asking_message = 'Hmn... what is the prefix than?'
        print(asking_message)
        for i, text in enumerate(prefix):
            print("[" + str(i + 1) + "] " + text + '...')
        print("[0] CANCEL")

        try:
            search_prefix_index = int(input())
            search_prefix = prefix[search_prefix_index - 1]

        except:
            print('NOPE!! Try again')
            search_prefix = self.ask_search_prefix()

        return search_prefix


class searchResult(object):
    def __init__(self):
        super(searchResult, self).__init__()
        self.search_input = dict(articleName="", lang="en")
        self.search_term = ''
        self.client = Algorithmia.client(auth_key['algorithmia']['apikey'])
        self.algo = self.client.algo('web/WikipediaParser/0.1.2')
        self.algo.set_options(timeout=300)  # optional

    def get_search_result_from_wiki(self, search_term):
        assert isinstance(search_term, str)
        result_list = sorted(RAW_DATA_PATH.glob(search_term + '_*' + '.json'))
        if result_list:
            print('Ahh...you already have this search!')
            with result_list[0].open() as json_file:
                search_result = json.load(json_file)
        else:
            self.search_input['articleName'] = search_term
            search_result = self.algo.pipe(self.search_input).result
            self.save_search_result_to_json(search_term, search_result)

        return search_result

    def save_search_result_to_json(self, search_term, search_result):
        filename = search_term + '_' + search_result['pageid'] + '.json'
        filename = RAW_DATA_PATH.joinpath(filename)
        with open(filename, 'w') as outfile:
            json.dump(search_result, outfile, sort_keys=True, indent=4, ensure_ascii=False)

    def get_content_processed(self, search_result, nr_of_setences=10):
        content_processed = ''
        content_processed_list = search_result['content'].replace("'", "`").split('\n')
        content_processed_list = [line for line in content_processed_list if
                                  (line.strip() and not line.strip().startswith('='))]
        content_processed = content_processed.join(content_processed_list)
        sent_text_list = nltk.sent_tokenize(content_processed)
        return sent_text_list[:nr_of_setences]


class ibmWatson(object):

    def __init__(self):
        super(ibmWatson, self).__init__()
        self.authenticator = IAMAuthenticator(auth_key['nlu_watson']['apikey'])
        self.nlu = NaturalLanguageUnderstandingV1(
            version=auth_key['nlu_watson']['version'],
            authenticator=self.authenticator)
        self.nlu.set_service_url(auth_key['nlu_watson']['url'])

    def get_keywords_from_sentences(self, sentences):
        response = self.nlu.analyze(
            text=sentences,
            features=Features(keywords=KeywordsOptions())).get_result()

        keywords_list = [keywords['text'] for keywords in response['keywords']]

        # print(json.dumps(response, indent=2))
        return keywords_list


class googleSearch(object):

    def __init__(self, search_term=None):
        super(googleSearch, self).__init__()
        self.api_key = auth_key['Google']['apikey']
        self.cse_id = auth_key['Google']['searchEng']
        self.search_term = search_term
        self.width = 1920
        self.height = 1080
        self.template = {0: {'width': 1920, 'height': 400,  'gravity': 'center'},
                         1: {'width': 1920, 'height': 1080, 'gravity': 'center'},
                         2: {'width': 800,  'height': 1080, 'gravity': 'west'}}


    def search_images_for_keyword(self, keyword):
        assert isinstance(keyword, str)
        query = '{} {}'.format(self.search_term, keyword)
        results = []
        service = build("customsearch", "v1", developerKey=self.api_key)
        results_raw = service.cse().list(q=query,
                                         cx=self.cse_id,
                                         searchType='image',
                                         num=3,
                                         rights=['cc_nonderived', 'cc_sharealike']).execute()
        for item in results_raw['items']:
            results.append(item['link'])
        return results

    def download_image(self, image_url, keyword):
        # Open the url image, set stream to True, this will return the stream content.
        filename = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_original.png')
        resp = requests.get(image_url, stream=True)
        resp.raise_for_status()
        # Open a local file with wb ( write binary ) permission.
        local_file = open(filename, 'wb')
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        resp.raw.decode_content = True
        # Copy the response stream raw data to local image file.
        shutil.copyfileobj(resp.raw, local_file)
        # Remove the image url response object.
        del resp

    def is_image_from_url_downloaded(self, keyword):
        filename = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword)
        file_in_dir = filename in filename.parent.iterdir()
        return file_in_dir

    def convert_image(self, keyword):
        input_file = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_original.png[0]')
        converted_file = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_converted.png')
        with Image(filename=str(input_file)) as original:
            with original.convert('png') as clone:
                clone.background_color = 'white'
                clone.blur(0, 9.)
                clone.resize(self.width, self.height)
                clone.composite(original, gravity='center')
                clone.extent(self.width, self.height)
                clone.extent(self.width, self.height)
                clone.save(filename=str(converted_file))

    def create_sentence_image(self, keyword, sentence):
        idx = randrange(0, 3)
        font = Font(path='tests/assets/League_Gothic.otf', size=64, color='white')
        sentence_image = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_sentences.png')
        with Image(width=self.template[idx]['width'],
                   height=self.template[idx]['height'],
                   background='transparent') as original:
            original.caption(sentence, font=font, gravity=self.template[idx]['gravity'])
            original.save(filename=str(sentence_image))

    def create_thumbnail(self, content):
        for keyword in content['keywords']:
            converted_file = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_converted.png')
            if converted_file.is_file():
                create_thumbnail = IMAGES_DATA_PATH.joinpath(self.search_term + '_thumbnail.jpg')
                with Image(filename=str(converted_file)) as original:
                    with original.convert('jpg') as clone:
                        clone.save(filename=str(create_thumbnail))
                break



class roger(object):

    def __init__(self, ):
        super(roger, self).__init__()

    st = searchTerm()
    st.search_term = st.ask_search_term()
    st.search_prefix = st.ask_search_prefix()
    print('Okay! I`ll look "{} {}" for you.'.format(st.search_prefix, st.search_term))

    sr = searchResult()
    result = sr.get_search_result_from_wiki(st.search_term)
    result = sr.get_content_processed(result)

    nlu = ibmWatson()
    glg = googleSearch(st.search_term)
    content = []
    for sentence in result:
        content.append({'text': sentence, 'keywords': nlu.get_keywords_from_sentences(sentence)})

    for elem in content:
        for keyword in elem['keywords']:
            elem['imageUrl'] = []
            imageUrl = glg.search_images_for_keyword(keyword)
            if imageUrl:
                elem['imageUrl'] = imageUrl
                break

    for i, elem in enumerate(content):
        for url, keyword in zip(elem['imageUrl'], elem['keywords']):
            print('Downloading {} of {}.'.format(i+1, len(content)))
            if glg.is_image_from_url_downloaded(keyword):
                print('Already here, jow!')
                break
            else:
                try:
                    glg.download_image(url, keyword)
                    glg.convert_image(keyword)
                    glg.create_sentence_image(keyword,  elem['text'])
                    break
                except HTTPError:
                    print('Download error, trying the next url')
                except OSError:
                    print('Download error, trying the next url')
    glg.create_thumbnail(content[0])



roger()
