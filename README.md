PLTSpeed
=======================

PLTSpeed captures and analyzes Chrome browsing traces in order to extract dependency relationship between activities. It is a continuation of works done before in [WProf] and [WProf-M] papers.

Setup
-----
Refer to [chrome-remote-interface] for the latest set up.
[chrome-remote-interface]:https://github.com/cyrus-and/chrome-remote-interface

### Install chrome-remote-interface

    npm install chrome-remote-interface

### Chrome/Chromium

#### Desktop

Start Chrome with the `--remote-debugging-port` option, for example:

    google-chrome --remote-debugging-port=9222

##### Headless

Since version 59, additionally use the `--headless` option, for example:

    google-chrome --headless --remote-debugging-port=9222

#### Android

Plug the device and enable the [port forwarding][adb], for example:

    adb forward tcp:9222 localabstract:chrome_devtools_remote

[adb]: https://developer.chrome.com/devtools/docs/remote-debugging-legacy

#### Note
You might find the following flags usefull depending on your use case:PLTSpeed

    google-chrome-stable --remote-debugging-port=9222 --start-maximized  --ignore-certificate-errors --user-data-dir=$TMPDIR/chrome-profiling --no-default-browser-check

[WProf]: http://www3.cs.stonybrook.edu/~arunab/papers/wprof.pdf
[WProf-M]:http://www3.cs.stonybrook.edu/~arunab/papers/wprofm.pdf

### Usage
#### Collect traces
- Install all required python modules in main.py
- Put the list of Web sites you want to analyze in live_test.txt
- Configure  `bases_dir`, `repeat_no` variables in main.py based on your preferences.
- Run main.py with python > 3.3



	python3.5 main.py   
	

#### Analyze traces
- Configure  `_experiment_dir` in analyze.py.
- Run `analyze.py` with python > 3.3

	python3.5 main.py

