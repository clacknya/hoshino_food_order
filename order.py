#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os.path import dirname, join

import json
import lxml.html
import cssselect
import random

from hoshino import Service, R
from hoshino.typing import CQEvent, MessageSegment
from hoshino.util import escape
from hoshino.aiorequests import get, post

sv = Service('点餐姬', help_='''
[点餐 菜名] 进行点餐
'''.strip())

# 美食杰
class meishij:

	# URL_QUERY = 'https://m.meishij.net/search.php?q=%s'
	URL_QUERY = 'https://so.meishi.cc/index.php?q=%s'

	async def order(self, name: str) -> dict:

		URL = self.URL_QUERY % name

		sv.logger.info(f"query {URL}")
		r = await get(URL)

		html = lxml.html.fromstring(await r.text)
		items = html.cssselect('div[class$="_cpitem"] > a.img > img')
		item = random.choice(items)

		return {
			'name': item.get('alt', 'NoName'),
			'img':  item.get('src', ''),
		}

# 心食谱
class xinshipu:

	URL_QUERY = 'https://www.xinshipu.com/doSearch.html?q=%s'

	async def order(self, name: str) -> dict:

		URL = self.URL_QUERY % name

		sv.logger.info(f"query {URL}")
		r = await get(URL)

		html = lxml.html.fromstring(await r.text)
		items = html.cssselect('a.shipu > div.v-pw > img')
		item = random.choice(items)

		return {
			'name': item.get('alt', 'NoName'),
			'img':  item.get('src', ''),
		}

# 美食天下
# class meishichina:

	# URL_QUERY = 'https://home.meishichina.com/search/%s/'

	# async def order(self, name: str) -> dict:

		# URL = URL_QUERY % name

		# r = await get(URL)

		# html = lxml.html.fromstring(await r.text)
		# items = html.cssselect('#search_res_list li')
		# item = random.choice(items)

		# return {
		# }

def load_config(filename: str) -> dict:
	with open(filename, 'r') as f:
		return json.load(f)

config = load_config(join(dirname(__file__), 'config.json'))

async def query(text: str) -> str:
	if not hasattr(query, 'waiter'):
		query.waiter = {
			'meishij':  meishij,
			'xinshipu': xinshipu,
		}[config.get('source', 'meishij')]()
	info = await query.waiter.order(text)
	return MessageSegment.image(info['img']) + info['name']

@sv.on_prefix('点餐')
async def order(bot, ev: CQEvent):
	s = escape(ev.message.extract_plain_text().strip())
	msg = await query(s)
	await bot.send(ev, msg, at_sender=True)
