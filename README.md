WProfX
=======================

WProfX captures and analyzes Chrome browsing traces in order to extract dependency relationship between activities. It is a continuation of works done before in [WProf] and [WProf-M] papers.

Setup
-----
Refer to [chrome-remote-interface] for the latest set up.
[chrome-remote-interface]:https://github.com/cyrus-and/chrome-remote-interface
[chrome-55]:http://www.slimjetbrowser.com/chrome/lnx/chrome64_55.0.2883.75.deb

### Install google-chrome-stable

	wget http://www.slimjetbrowser.com/chrome/lnx/chrome64_55.0.2883.75.deb

### Install chrome-remote-interface

    npm install chrome-remote-interface@v0.23.3

### Chrome/Chromium
 

#### Desktop

Start Chrome with the `--remote-debugging-port` option, for example:

    google-chrome-stable --remote-debugging-port=9222

##### Headless

	sudo apt-get install xvfb
	
	/usr/bin/Xvfb :7 -screen 0 1024x768x24 &

#### Android

Plug the device and enable the [port forwarding][adb], for example:

    adb forward tcp:9222 localabstract:chrome_devtools_remote

[adb]: https://developer.chrome.com/devtools/docs/remote-debugging-legacy

#### Note
You might find the following flags usefull depending on your use case

    DISPLAY=:7 google-chrome-stable --remote-debugging-port=9222 --start-maximized  --ignore-certificate-errors --user-data-dir=$TMPDIR/chrome-profiling --no-default-browser-check

[WProf]: http://www3.cs.stonybrook.edu/~arunab/papers/wprof.pdf
[WProf-M]:http://www3.cs.stonybrook.edu/~arunab/papers/wprofm.pdf

### Usage

#### Collect traces

Install all required python modules in `main.py`, `trace_parser.py` and `analyze.py`.

	sudo pip3 install tldextract
	
	sudo pip3 install pyOpenssl
	
	sudo pip3 install coloredlogs
	
	sudo pip3 install networkx==1.9
	
	sudo pip3 install matplotlib
	
	sudo pip3 install bokeh

	sudo apt-get install python3-tk
	
- Put the list of Web sites you want to analyze in `live_test.txt`.

- Configure  `bases_dir`, `repeat_no` variables in main.py based on your preferences.

- Run `main.py` with python > 3.3 
	

#### Analyze traces

- Configure  `_experiment_dir` in `analyze.py`.

- Run `analyze.py` with python > 3.3

Anlaysi output format
-----
The output of `analyze.py` is a `JSON` file which embodies all activities involved in a page load process. Moreover, it will give information about start and end time of activities and moe interestingly the dependency relationship between such activities.

A sample genereated `JSON` file can be found at the output directory.

For each URL, a list of  entries carry information about all objects involved in processing that URL. Information include start/end time, mimeType and whether that each object has been called from a script or from the main HTML source.

```json
"url": "http://www.cnn.com/",
"startTime": 0.0,
"mimeType": "text/html",
"id": "31739.1",
"fromScript": "Null",
"transferSize": 4079,
"endTime": 125.068,
"activityId": "Networking_0",
"responseReceivedTime": 98.156,
"statusCode": 200
```

The entry with `"id": "Deps"` carries information regarding the dependency between activities. 

For example, the following snippet states that  `Scripting_71` depends on `Networking_144` to be completed. Note that a `-1` for the  `time` value denotes a complete dependency relationship, i.e., `a1` needs to be finished before `a2` can start.

```json
{
	"time": -1,
	"a2": "Scripting_71",
	"a1": "Networking_144"
},
```

Whereas, a partial dependency in which, `time` value denotes the actual time in `milliseconds` when `a2` can start.

```json
{
  "time": 1003.723,
  "a2": "Networking_30",
  "a1": "Scripting_7"
}
```
