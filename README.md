PLTSpeed
=======================

PLTSpeed captures and analyzes Chrome browsing traces in order to extract dependency relationship between activities. It is a continuation of works done before in [WProf] and [WProf-M] papers.

Setup
-----
Refer to [chrome-remote-interface] for the latest set up.
[chrome-remote-interface]:https://github.com/cyrus-and/chrome-remote-interface
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
You might find following flags usefull depending on your use case:
    google-chrome-stable --remote-debugging-port=9222 --start-maximized  --ignore-certificate-errors --user-data-dir=$TMPDIR/chrome-            profiling --no-default-browser-check


[WProf]: http://www3.cs.stonybrook.edu/~arunab/papers/wprof.pdf
[WProf-M]:http://www3.cs.stonybrook.edu/~arunab/papers/wprofm.pdf
