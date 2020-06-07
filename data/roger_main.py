#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : roger_main.py
@Date    : 10/31/19 11:43 PM
@Project : roger_trendsetter
@Author  : juangp3
"""
from builtins import dict

import Algorithmia
import json
import nltk
from pathlib import Path

import requests
import shutil

from ibm_watson import NaturalLanguageUnderstandingV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# system imports
from ibm_watson.natural_language_understanding_v1 import Features, KeywordsOptions
from googleapiclient.discovery import build
from wand.image import Image
from wand.font import Font
from random import randrange
from xml.etree import ElementTree as ET
from srt import Subtitle, compose
from datetime import timedelta
import upload_video


auth_key = {'algorithmia': {'apikey': 'simnbKMNi+ynZMGZJdKe8d2CjJu1'},
            'nlu_watson': {'apikey': 'dx9aHzStLwZRW6Ltkjb5nAJjju9iANxLqQQXy026jLV9',
                           'version': '2019-11-06',
                           'url': 'https://gateway-lon.watsonplatform.net/natural-language-understanding/api'},
            'Google': {'apikey': 'AIzaSyBQ0jKnW3SYaGJitVnNGtwULwwFnvUoS_I',
                       'searchEng': '012896964214635737899:9rpxasrajfj'}}

MODULE_PATH = Path.cwd()
RAW_DATA_PATH = MODULE_PATH.joinpath('raw')
IMAGES_DATA_PATH = MODULE_PATH.joinpath('images')


class SearchTerm(object):

    def __init__(self):
        super(SearchTerm, self).__init__()
        self.search_term = ''
        self.search_prefix = ''

    @staticmethod
    def ask_search_term():
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

        except Exception:
            print('NOPE!! Try again')

        self.ask_search_prefix = search_prefix
        return self.ask_search_prefix


class SearchResult(object):
    def __init__(self):
        super(SearchResult, self).__init__()
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
            with result_list[0].open(encoding="utf8") as json_file:
                search_result = json.load(json_file)
        else:
            self.search_input['articleName'] = search_term
            search_result = self.algo.pipe(self.search_input).result
            self.save_search_result_to_json(search_term, search_result)

        return search_result

    @staticmethod
    def save_search_result_to_json(search_term, search_result):
        filename = search_term + '_' + search_result['pageid'] + '.json'
        filename = RAW_DATA_PATH.joinpath(filename)
        with open(filename, 'w', encoding='utf8') as outfile:
            json.dump(search_result, outfile, sort_keys=True, indent=4, ensure_ascii=False)

    @staticmethod
    def get_content_processed(search_result, nr_of_setences=10):
        content_processed = ''
        content_processed_list = search_result['content'].replace("'", "`").split('\n')
        content_processed_list = [line for line in content_processed_list if
                                  (line.strip() and not line.strip().startswith('='))]
        content_processed = content_processed.join(content_processed_list)
        sent_text_list = nltk.sent_tokenize(content_processed)
        return sent_text_list[:nr_of_setences]


class IbmWatson(object):

    def __init__(self):
        super(IbmWatson, self).__init__()
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
        return keywords_list


class GoogleSearch(object):

    def __init__(self, search_term=None):
        super(GoogleSearch, self).__init__()
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
                                         num=5,
                                         rights='(cc_publicdomain%7Ccc_attribute%7Ccc_sharealike).-(cc_noncommercial%7Ccc_nonderived)',
                                         imgSize='XLARGE').execute()
        for item in results_raw['items']:
            results.append(item['link'])
        return results

    def download_image(self, image_url, keyword):
        # Open the url image, set stream to True, this will return the stream content.
        filename = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword.replace('.', '') + '_original.png')
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
        return filename

    def is_image_from_url_downloaded(self, keyword):
        filename = IMAGES_DATA_PATH.joinpath(self.search_term + '_' + keyword + '_converted.png')
        filename in filename.parent.iterdir()
        return filename

    def convert_image(self, input_file):
        converted_file = IMAGES_DATA_PATH.joinpath(input_file.name.replace('_original.png', '_converted.png'))
        with Image(filename=str(input_file)) as original:
            with original.convert('png') as clone:
                clone.background_color = 'white'
                clone.blur(0, 9.)
                clone.resize(self.width, self.height)
                clone.composite(original, gravity='center')
                clone.extent(self.width, self.height)
                clone.extent(self.width, self.height)
                clone.save(filename=str(converted_file))
        return converted_file

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


class Fcpxml(object):
    def __init__(self, search_term, content):
        self.search_term = search_term
        self.content = content
        self.template = 'VideoTemplate.fcpxml'
        self.audio_dic = {'AUDIO_NAME': '333795__frankum__electronic-music-loop-m1.mp3',
                          'AUDIO_PATH': 'file://localhost/C:/Users/juan_/PycharmProjects/roger_trendsetter/data/333795__frankum__electronic-music-loop-m1.mp3'}
        self.asset_dic = {}
        self.clip_duration = 10
        self.clip_start_time = 5
        self.create_asset_dic()
        self.create_fcpxml()

    def create_asset_dic(self):
        for i, element in enumerate(self.content):
            self.asset_dic['Image' + str(i+1)] = {'FILE_NAME' + str(i+1): element['imagePath'].name,
                                                  'FILE_PATH' + str(i+1): element['imagePath'].as_uri()}

    def create_fcpxml(self):
        datafile = ET.parse(self.template)
        for el in datafile.find('resources'):
            if 'id' in el.attrib:
                if 'Image' in el.attrib['id']:
                    asset = self.asset_dic[el.attrib['id']]
                    el.attrib['name'] = asset[el.attrib['name']]
                    el.attrib['src'] = asset[el.attrib['src']]
                elif 'Audio' in el.attrib['id']:
                    el.attrib['name'] = self.audio_dic[el.attrib['name']]
                    el.attrib['src'] = self.audio_dic[el.attrib['src']]

        t = self.clip_start_time
        for el in datafile.find('library/event/project/sequence/spine'):
            if 'ref' in el.attrib:
                if 'Image' in el.attrib['ref']:
                    asset = self.asset_dic[el.attrib['ref']]
                    el.attrib['name'] = asset[el.attrib['name']]
                    el.attrib['offset'] = '{0}s'.format(t)
                    asset['clipStart'] = t
                    t += self.clip_duration
                    asset['clipEnd'] = t
                elif 'Transition' in el.attrib['ref']:
                    el.attrib['offset'] = '{0}/2s'.format(t*2 - 1)
                elif 'r1' in el.attrib['ref'] and el.find('spine'):
                    for audio in el.find('spine'):
                        audio.attrib['name'] = self.audio_dic[audio.attrib['name']]
        datafile.write(self.search_term + '.fcpxml')

    @property
    def get_clips_asset(self):
        return self.asset_dic


class SubtitleGenerator(object):
    def __init__(self, search_term, content, clips_asset):
        self.clips_asset = clips_asset
        self.content = content
        self.search_term = search_term

    def create_subtitle(self):
        subs = []
        out_filename = self.search_term + '.srt'
        for i, (text, time) in enumerate(zip(self.content, list(self.clips_asset.values()))):
            ti = timedelta(seconds=time['clipStart'])
            te = timedelta(seconds=time['clipEnd'] - 1, microseconds=416000)
            subs.append(Subtitle(index=i + 1, start=ti, end=te, content=text['text']))
        try:
            with open(out_filename, 'w') as out_file:
                out_file.write(compose(subs))
        except Exception:
            print(out_filename + ' not created.')


class Roger(object):
    def __init__(self, ):
        super(Roger, self).__init__()
        self.st = SearchTerm()
        self.sr = SearchResult()
        self.nlu = IbmWatson()
        self.run()

    @staticmethod
    def create_video_snippet(search_title, search_url, content):
        description = 'Hi, all. This video was created by Roger, the Robot\n' \
                      'Just a side project to learn python and some APIs.\n\n' \
                      'Links and references:\n'

        api_refs = 'Content reference: ' + search_url + '\n' \
                   'Music:\nElectronic music loop M1 - By Frankum ' \
                   '- https://freesound.org/s/333795/\n' \
                   'Algorithmia : https://algorithmia.com/.\n' \
                   'IMB Watson - Natural Language Understanding : ' \
                   'https://watson-developer-cloud.github.io/node-sdk/debug/' \
                   'classes/naturallanguageunderstandingv1.html.\n' \
                   'Google API : https://developers.google.com/.\n' \
                   'YouTube API: https://developers.google.com/youtube/v3.' \
                   'wand : http://docs.wand-py.org/en/0.6.1/.'

        img_ref = ''
        for element in content:
            img_ref = img_ref + '{}\n'.format(element['imageUrl_received'])

        video_snippet = {"snippet": {"title": search_title,
                                     "description": '{} {}\n\n{}'.format(description, img_ref, api_refs),
                                     "tags": content[0]['keywords'],
                                     "categoryId": "22"},
                         "status": {"privacyStatus": "private"}}
        return video_snippet

    def wait_video(self):
        asking_message = 'Almost there...let me know when the video is done!?'
        print(asking_message)
        print("[0] CANCEL")
        print("[1] Done...Upload my video!")

        try:
            result = int(input())
        except Exception:
            print('NOPE!! Try again')
            self.wait_video()
        return result

    def run(self):
        st = self.st
        st.search_term = st.ask_search_term()
        st.search_prefix = st.ask_search_prefix()
        search_title = "{} {}".format(st.search_prefix, st.search_term)
        print('Okay! I`ll look "{}" for you.'.format(search_title))

        sr = self.sr
        result = sr.get_search_result_from_wiki(st.search_term)
        search_url = result['url']
        result = sr.get_content_processed(result)

        nlu = self.nlu
        glg = GoogleSearch(st.search_term)
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
                image_path = glg.is_image_from_url_downloaded(keyword)
                if image_path.exists():
                    print('Already here, jow!')
                    elem['imagePath'] = image_path
                    elem['imageUrl_received'] = url
                    break
                else:
                    try:
                        print(st.search_term + ' ' + keyword)
                        image_path = glg.download_image(url, keyword)
                        elem['imageUrl_received'] = url
                        image_path = glg.convert_image(image_path)
                        elem['imagePath'] = image_path
                        #glg.create_sentence_image(keyword,  elem['text'])
                        break
                    except Exception:
                        print('Download error, trying the next url')
            else:
                elem['imagePath'] = content[i-1]['imagePath']

        video_snippet = self.create_video_snippet(search_title, search_url, content)

        glg.create_thumbnail(content[0])
        video_fmt = Fcpxml(st.search_term, content)
        sub = SubtitleGenerator(st.search_term, content, video_fmt.get_clips_asset)
        sub.create_subtitle()
        if self.wait_video() == 1:
            upload_video.UpVid(video_snippet, st.search_term)
        else:
            print("Probably everything is ready, but you have cancelled!")



#########################################


if __name__ == '__main__':
    Roger()



