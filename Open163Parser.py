from bs4 import BeautifulSoup as Soup
from urllib import parse as urlparse
from time import time
import requests, sys, re, json, os
from queue import Queue
from threading import Thread
from argparse import ArgumentParser
from os.path import (
	realpath, dirname, 
	join as pathjoin,
	)


class FlvcdAPICaller(object):
	"""
	Flvcd API caller.
	"""

	URL = "http://www.flvcd.com/parse.php"
	VideoPattern = re.compile(r'clipurl = "(.+)";var cliptitle = "(.+)";')
	SrtPattern = re.compile(r'<a href="([^>]+)?"><font color="green">双语字幕</font>')

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
		res = requests.get(self.URL, params=payload)
		if res.status_code != 200:
			print("Unable to access Flvcd API.")
		else:
			# Flvcd still uses the damn GB2312.
			# This will fix the Chinese mess, using chardet module.
			res.encoding = res.apparent_encoding
			videoMatch = self.VideoPattern.search(res.text)
			if not videoMatch:
				print("No video found.")
			else:
				videoURL, videoName = videoMatch.group(1), videoMatch.group(2)[:-4]
				videoInfo = {
						"url":videoURL,
						"name":videoName,
					}
				srtMatch = self.SrtPattern.search(res.text)
				if not srtMatch:
					print("No subtitle found.")
				else:
					srtURL = srtMatch.group(1)
					videoInfo["srt"] = srtURL

				return videoInfo


class Open163Parser(object):
	"""Get course videoe URLs from www.open.163.com"""

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
	def __init__(self, queue, parser, APIcaller):
		super().__init__()
		self.queue = queue
		self.parser = parser
		self.APIcaller = APIcaller

	def run(self):
		while True:
			url = self.queue.get()
			videoInfo = self.APIcaller.getVideoInfo(url)
			self.parser.putResult(videoInfo)
			self.queue.task_done()


def ExtractVideoInfo(courseURL):
	"""
	提取视频信息。
	"""
	queue = Queue()
	APIcaller = FlvcdAPICaller()
	parser = Open163Parser(courseURL)
	for i in range(10):
		worker = Worker(queue, parser, APIcaller)
		worker.daemon = True
		worker.start()
	parser.fillQ(queue)
	queue.join()
	videoList = parser.getResult()
	videoInfo = {
		"courseURL":courseURL,
		"videoList":videoList,
	}
	# dump complete video information.
	json.dump(videoInfo, open("videoList.json", "w"))
	print("Complete video information written to videoList.json.")
	# dump video URLs.
	urls = []
	for video in videoList:
		urls.append(video['url']+'\n')
	with open('urls.txt', 'w') as out:
		out.writelines(urls)
	print("Video URLs written to urls.txt.")


def getSubtitles(videoListFile):
	"""
	下载字幕。
	"""
	try:
		videoInfo = json.load(open(videoListFile))
		videoList = videoInfo['videoList']
	except IOError:
		print("Video information file not found.")
	print("Totally {} subtitles".format(
		len(videoList)
		)
	)
	if not os.path.exists("Subtitles"):
		os.mkdir("Subtitles")
	os.chdir("Subtitles")
	for video in videoList:
		res = requests.get(video['srt'])
		with open(video['name']+'.srt', 'w') as out:
			out.write(res.text)
	os.chdir("..")


def renameVideoes(videoListFile, videoFilePath):
	"""
	根据记录在 videoList.json 中的视频信息，更改下载好的视频的文件名。
	"""
	try:
		videoInfo = json.load(open(videoListFile))
		videoList = videoInfo['videoList']
	except IOError:
		print("Video information file not found.")
	videoNames = {
		os.path.split(v['url'])[1] : v['name'] for v in videoList
	}
	for f in os.listdir(videoFilePath):
		if f.endswith('.flv') and f in videoNames:
			os.rename(
				pathjoin(videoFilePath, f), 
				pathjoin(videoFilePath, videoNames[f]+'.flv'),
				)

def ArgParserInit():
	argparser = ArgumentParser()
	argparser.add_argument(
		"-c", "--courseURL",
		help="specify URL of the cousres on open.163.com"
		)
	argparser.add_argument(
		"-s", "--subtitle",
		help="given video information file extracted, get video subtitles",
		action="store_true",
		)
	argparser.add_argument(
		"-r", "--rename_video_dir",
		help="given video folder path, rename downloaded videoes",
		)
	return argparser


def main():
	argparser = ArgParserInit()
	args = argparser.parse_args()
	scriptDir = dirname(realpath(__file__))
	videoListFile = pathjoin(scriptDir, "videoList.json")
	if args.courseURL and not os.path.exists(videoListFile):
		ExtractVideoInfo(args.courseURL)
	if args.subtitle:
		getSubtitles(videoListFile)
	if args.rename_video_dir:
		renameVideoes(
			videoListFile,
			args.rename_video_dir,
		)
	if not any(vars(args).values()):
		argparser.print_help()


if __name__ == '__main__':
	main()