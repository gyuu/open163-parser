# Simple Open163 Parser

一个简单的网易公开课视频 URL 提取工具, 获取到 URL 后，就可以使用迅雷等下载工具在 PC 端下载网易公开课的视频。

视频URL提取使用了 flvcd.com 的服务，我只是解析了一下网页。

原本目的是为了下载 iOS7 的公开课。测试了一些另外的课程，有些会解析出错。如果有时间我会 review 一下……

## Dependencies

- Python3
- requests
- beautifulsoup4

## Usage

`$ python Open163Parser.py <course_url>`。

这里的 URL 需要是课程主页的 URL。例如 http://v.163.com/special/opencourse/ios7.html。

默认的行为是在终端打印出视频 URL 的列表，并将每堂课的信息，包括名字、视频URL、双语字幕URL，写入当前目录下的一个 json 文件中。有别的需求的自己改下就好啦。