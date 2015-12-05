# Simple Open163 Parser

一个简单的网易公开课视频 URL 提取工具, 获取到 URL 后，就可以使用迅雷等下载工具在 PC 端下载网易公开课的视频。

视频URL提取使用了 flvcd.com 的服务，我只是解析了一下网页。

原本目的是为了下载 iOS7 的公开课。测试了一些另外的课程，有些会解析出错。如果有时间我会 review 一下……

## Dependencies

- Python3
- requests
- beautifulsoup4

## Usage

`$ python Open163Parser.py -c <course_url>`

这里的 URL 需要是课程主页的 URL。例如 http://open.163.com/special/opencourse/ios7.html. 

视频的 URL 会写到当前目录的 `urls.txt` 文件中，复制到迅雷就可以下载了。

视频的完整信息，包括名字、视频URL、字幕URL，会写到当前目录的 `videoList.json` 中，主要是为了下面两个操作使用。想要做别的事情可以直接读这个文件。

`$ python Open163Parser.py -s`

下载视频的中英字幕文件。

`$ python Open163Parser.py -r VIDEO_FOLDER`

视频下载完成后，文件名不是视频名而是杂乱的字符串，这时候使用此命令给出视频文件夹的路径，来将视频重命名。
