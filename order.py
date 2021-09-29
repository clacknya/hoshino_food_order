#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, TypedDict

import os
import sys
import inspect
import json
import asyncio
import aiohttp
import aiofiles
import lxml.html
import cssselect
import random

from hoshino import Service, R
from hoshino.typing import CQEvent, MessageSegment
from hoshino.util import escape

PATH_ROOT = os.path.dirname(os.path.abspath(__file__))
PATH_CONFIG = os.path.join(PATH_ROOT, 'config.json')

sv = Service('点餐姬', help_='''
[点餐 菜名] 进行点餐
'''.strip())

class TypeFood(TypedDict):
	name:  str
	image: str

class base():

	BLANK = 'base64://R0lGODlhAQABAIAAAAUEBAAAACwAAAAAAQABAAACAkQBADs='

	def __init__(self):
		self.default_haaders = {
			'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0',
			'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
			'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
			'Accept-Encoding': 'gzip, deflate',
		}

	async def request(self, method: str, url: str, ctype: str, **kwargs) -> str:
		sv.logger.info(f"{method} {url}")
		async with aiohttp.ClientSession(headers=self.default_haaders, raise_for_status=True) as session:
			async with session.request(method, url, **kwargs) as resp:
				if ctype == 'byte':
					ret = await resp.read()
				elif ctype == 'text':
					ret = await resp.text()
				elif ctype == 'json':
					ret = await resp.json(content_type=None)
				else:
					raise Exception('Unknow content type')
		return ret

	# async def search(self, name: str) -> List:
		# raise NotImplementedError

	async def order(self, name: str) -> TypeFood:
		raise NotImplementedError

# 美食杰
class meishij(base):

	# URL_QUERY = 'https://m.meishij.net/search.php?q=%s'
	URL_QUERY = 'https://so.meishi.cc/index.php?q=%s'

	async def order(self, name: str) -> TypeFood:
		text = await self.request('GET', self.URL_QUERY % name, 'text')
		html = lxml.html.fromstring(text)
		nodes = html.cssselect('div[class$="_cpitem"] > a.img > img')
		if not nodes:
			return {}
		node = random.choice(nodes)
		return {
			'name':  node.get('alt'),
			'image': node.get('src'),
		}

# 心食谱
class xinshipu(base):

	URL_QUERY = 'https://www.xinshipu.com/doSearch.html?q=%s'

	async def order(self, name: str) -> TypeFood:
		text = await self.request('GET', self.URL_QUERY % name, 'text')
		html = lxml.html.fromstring(text)
		nodes = html.cssselect('a.shipu > div.v-pw > img')
		if not nodes:
			return {}
		node = random.choice(nodes)
		return {
			'name':  node.get('alt'),
			'image': node.get('src'),
		}

# 美食天下
# class meishichina:

	# URL_QUERY = 'https://home.meishichina.com/search/%s/'

	# async def order(self, name: str) -> TypeFood:
		# text = await self.request('GET', self.URL_QUERY % name, 'text')
		# html = lxml.html.fromstring(text)
		# nodes = html.cssselect('#search_res_list li')
		# if not nodes:
			# return {}
		# node = random.choice(nodes)
		# return {
		# }

# Yummly
class yummly(base):

	URL_QUERY = 'https://www.yummly.com/recipes?q=%s&taste-pref-appended=true'

	async def order(self, name: str) -> TypeFood:
		text = await self.request('GET', self.URL_QUERY % name, 'text')
		html = lxml.html.fromstring(text)
		script = html.cssselect('div.structured-data-info > script')[0]
		data = json.loads(script.text)
		items = data['itemListElement']
		if not items:
			return {}
		item = random.choice(items)
		return {
			'name':  item.get('name'),
			'image': item.get('image')[0],
		}

def load_config(filename: str) -> Dict:
	if not os.path.isfile(filename):
		return {}
	with open(filename, 'r') as f:
		return json.load(f)

config = load_config(PATH_CONFIG)

waiters = dict(filter(
	lambda x: issubclass(x[1], base) and x[1] != base,
	inspect.getmembers(sys.modules[__name__], inspect.isclass)
))
waiter = waiters[config.get('source', 'meishij')]()

@sv.on_prefix('点餐')
async def order(bot, ev: CQEvent):
	name = escape(ev.message.extract_plain_text().strip())
	info = await waiter.order(name)
	if info.get('image'):
		bytes = await waiter.request('GET', info['image'], 'byte')
		try:
			async with aiofiles.tempfile.NamedTemporaryFile('wb', delete=False) as f:
				await f.write(bytes)
			os.chmod(f.name, 0o644)
			msg = str(MessageSegment.image(f"file:///{f.name}")) + info.get('name', '')
			await bot.send(ev, msg, at_sender=True)
		finally:
			if os.path.isfile(f.name):
				os.remove(f.name)
	else:
		await bot.send(ev, info.get('name', f"本店没有{name}哦"), at_sender=True)

