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

from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# system imports
from ibm_watson.natural_language_understanding_v1 import Features, KeywordsOptions

auth_key = {'algorithmia': 'simnbKMNi+ynZMGZJdKe8d2CjJu1',
            'nlu_watson': {'apikey': 'dx9aHzStLwZRW6Ltkjb5nAJjju9iANxLqQQXy026jLV9',
                           'version': '2019-11-06',
                           'url': 'https://gateway-lon.watsonplatform.net/natural-language-understanding/api'}}

MODULE_PATH = Path.cwd()
RAW_DATA_PATH = MODULE_PATH.joinpath('raw')


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
        self.client = Algorithmia.client(auth_key['algorithmia'])
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


roger = searchTerm()
roger.search_term = roger.ask_search_term()
roger.search_prefix = roger.ask_search_prefix()
print('Okay! I`ll look "{} {}" for you.'.format(roger.search_prefix, roger.search_term))

search = searchResult()
result = search.get_search_result_from_wiki(roger.search_term)
result = search.get_content_processed(result)

nlu = ibmWatson()
struc = dict()
lista = []
for sentence in result:
    lista.append({'text': sentence, 'keywords': nlu.get_keywords_from_sentences(sentence)})



