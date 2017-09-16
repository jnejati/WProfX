PLTSpeed
=======================

PLTSpeed captures and analyzes Chrome browsing traces in order to extract dependency relationship between activities. It is a continuation of works done before in [WProf] and [WProf-M] papers.

Setup
-----

### Chrome/Chromium

#### Desktop

Enable Chrome/Chromium remote debugging:
google-chrome-stable --remote-debugging-port=9222 --start-maximized  --ignore-certificate-errors --user-data-dir=$TMPDIR/chrome-profiling --no-default-browser-check
npm install chrome-remote-interface

This module is one of the many [third-party protocol clients][3rd-party].

[WProf]: http://www3.cs.stonybrook.edu/~arunab/papers/wprof.pdf
[WProf-M]:http://www3.cs.stonybrook.edu/~arunab/papers/wprofm.pdf
