#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@File    : roger_main.py
@Date    : 10/31/19 11:43 PM
@Project : roger_trendsetter
@Author  : juangp3
"""
import unittest


# system imports

class searchTerm(object):

    def __init__(self):
        super(searchTerm, self).__init__()
        self.search_term = ''

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
            print("[" + str(i+1) + "] " + text + '...')
        print("[0] CANCEL")


        try:
            search_prefix_index = int(input())
            search_prefix = prefix[search_prefix_index-1]

        except :
            print('NOPE!! Try again')
            search_prefix = self.ask_search_prefix()

        return search_prefix


roger = searchTerm()
roger.search_term = roger.ask_search_term()
roger.search_term = roger.ask_search_prefix() + ' ' + roger.search_term
print('Okay! I`ll look "{}" for you.'.format(roger.search_term))