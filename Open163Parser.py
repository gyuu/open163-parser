from bs4 import BeautifulSoup as Soup
from urllib import parse as urlparse
from time import time
import requests, sys, re, json
from queue import Queue
from threading import Thread

class Open163Parser(object):
	"""Get course videoe URLs from www.open.163.com"""

	FlvcdAPI = "http://www.flvcd.com/parse.php"
	VideoPattern = re.compile(r'clipurl = "(.+)";var cliptitle = "(.+)";')
	SrtPattern = re.compile(r'<a href="([^>]+)?"><font color="green">双语字幕</font>')

	def __init__(self, courseURL):
		self.courseURL = courseURL
		self.resQ = Queue()

	def _parseSrtURL(self, srtURL):
		"""
		接受匹配到的双语字幕URL为参数，提取出中英文字幕URL。
		如果只需要双语字幕则不需要调用此接口。
		"""
		encodedQuery = urlparse.urlsplit(srtURL).query
		# note the title of srt is encoded in GB2312.
		srtInfo = urlparse.parse_qs(encodedQuery, encoding='gb2312')
		srtInfo["cn-en"] = srtURL
		return srtInfo

	def getLectureURLs(self, courseURL):
		"""
		根据课程主页面提取出每一节课的URL，用于调用 Flvcd API。
		"""
		res = requests.get(courseURL)
		if res.status_code != 200:
			print("Unable to find course page.")
		else:
			doc = Soup(res.text, "html.parser")
			lectures = doc.find(id="list2").find_all("td", "u-ctitle")
			lectURLs = []
			for lect in lectures:
				lectURLs.append(lect.a["href"])
			print("Totally ", len(lectURLs), "lectures.")
			return lectURLs

	def getVideoInfo(self, lectURL):
		"""
		使用每一节课的URL，调用 Flvcd API。
		解析返回页面，提取出视频名称、视频下载地址、字幕信息。
		将视频的所有信息放入字典中返回。
		"""
		# print("Processing ", lectURL)
		payload = {
			"kw":lectURL,
		}
		res = requests.get(self.FlvcdAPI, params=payload)
		if res.status_code != 200:
			print("Unable to access Flvcd API.")
		else:
			# Flvcd still uses the damn GB2312.
			# This will fix the Chinese mess, using chardet module.
			res.encoding = res.apparent_encoding
			videoMatch = self.VideoPattern.search(res.text)
			if not videoMatch:
				print("Parsing Error.")
			else:
				videoURL, videoName = videoMatch.group(1), videoMatch.group(2)[:-4]
				videoInfo = {
						"url":videoURL,
						"name":videoName,
					}
				srtMatch = self.SrtPattern.search(res.text)
				if not srtMatch:
					print("Parsing Error.")
				else:
					srtURL = srtMatch.group(1)
					videoInfo["srt"] = srtURL

				return videoInfo

	def go(self):
		"""
		Single Thread Worker.
		"""
		lectURLs = self.getLectureURLs(self.courseURL)
		videoList = []
		for url in lectURLs:
			videoList.append(self.getVideoInfo(url))
		return videoList

	# multithreading methods below:

	def fillQ(self, queue):
		"""
		fill the queue for multithreading.
		"""
		lectURLs = self.getLectureURLs(self.courseURL)
		for url in lectURLs:
			queue.put(url)

	def putResult(self, videoInfo):
		"""
		put videoInfo into result queue.
		"""
		self.resQ.put(videoInfo)

	def getResult(self):
		"""
		return results.
		"""
		videoList = []
		while self.resQ.qsize() > 0:
			videoList.append(self.resQ.get())
		return tuple(videoList)


class Worker(Thread):
	"""
	Worker thread to call FlvcdAPIs.
	"""
	def __init__(self, queue, parser):
		super().__init__()
		self.queue = queue
		self.parser = parser

	def run(self):
		while True:
			url = self.queue.get()
			videoInfo = self.parser.getVideoInfo(url)
			self.parser.putResult(videoInfo)
			self.queue.task_done()


def SingleThreadDown():
	"""
	单线程调用 FlvcdAPI。
	"""
	courseURL = sys.argv[1]
	parser = Open163Parser(courseURL)
	videoList = parser.go()
	for video in videoList:
		print(video)


def MultiThreadDown():
	"""
	多线程调用 FlvcdAPI。
	"""
	queue = Queue()
	parser = Open163Parser(sys.argv[1])
	for i in range(10):
		worker = Worker(queue, parser)
		worker.daemon = True
		worker.start()
	parser.fillQ(queue)
	queue.join()
	videoList = parser.getResult()
	json.dump(videoList, open("videoList.json", "w"))
	for video in videoList:
		print(video["url"])


def testFunc(func):
	"""
	测试函数。
	"""
	print("Now running", func.__name__)
	t_start = time()
	func()
	t_end = time()
	print(func.__name__, "cost time is: {:.2f}s".format(t_end - t_start))


if __name__ == '__main__':
	# testFunc(SingleThreadDown)
	testFunc(MultiThreadDown)