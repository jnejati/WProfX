var fs = require('fs');
var Chrome = require('chrome-remote-interface');
var summary = require('./util/browser-perf-summary')

//var TRACE_CATEGORIES = ["-*", "devtools.timeline", "disabled-by-default-devtools.timeline", "disabled-by-default-devtools.timeline.frame", "toplevel", "blink.console", "disabled-by-default-devtools.timeline.stack", "disabled-by-default-devtools.screenshot", "disabled-by-default-v8.cpu_profile"];
var TRACE_CATEGORIES = ["-*", "toplevel", "blink.console", "disabled-by-default-devtools.timeline", "devtools.timeline", "disabled-by-default-devtools.timeline.frame", "devtools.timeline.frame","disabled-by-default-devtools.timeline.stack", "disabled-by-default-v8.cpu_profile",  "disabled-by-default-blink.feature_usage", "blink.user_timing", "v8.execute", "netlog"];
var rawEvents = [];
var myArgs = process.argv.slice(2);

Chrome(function (chrome) {
    with (chrome) {
        Page.enable();
	Network.enable();
        Network.setCacheDisabled;
	var p1 = Network.clearBrowserCache();
        var p2 = Network.clearBrowserCookies();
        //var p3 = Network.emulateNetworkConditions({offline: false, latency: 5, downloadThroughput: 20000000, uploadThroughput: 20000000});
	//var p4 = Promise.all([p1, p2, p3]).then(function(){
	var p4 = Promise.all([p1, p2]).then(function(){
		console.log('Cache and Cookies cleared.');
		//console.log('Network emulation set.');
	})
	.catch((error)=> {
		    console.error(error,'Promise error');
		      });
	var p5 = p4.then(function (){
	        Tracing.start({ "categories":   TRACE_CATEGORIES.join(','),
			        "options":      "sampling-frequency=10000"  // 1000 is default and too slow.
				   });
	});
        var p6 = p5.then(function(){
	     Page.navigate({'url': myArgs[0]},
                           function () {
                              Page.captureScreenshot(function (err, res) {
                              var buf = new Buffer(res.data, 'base64');
                              var imageFile = myArgs[3] + '.png'
                              fs.writeFileSync(imageFile, buf);
            });
           });
	});
        
        Page.loadEventFired(function (data) {
           Tracing.end(function () {
                              Page.captureScreenshot(function (err, res) {
                              var buf = new Buffer(res.data, 'base64');
                              var imageFile = myArgs[3] + '.png'
                              fs.writeFileSync(imageFile, buf);
            });
           });
           //process.kill(parseInt(myArgs[4]));
           var _times = {};
           _times.load = data.timestamp;
           var times_file = myArgs[2] + '.times';
           fs.writeFileSync(times_file, JSON.stringify(_times, null, 0));
        });
        Tracing.tracingComplete(function () {
            var traceFile = myArgs[1] + '.trace';
            var summaryFile = myArgs[2];
	    rawEvents = rawEvents.map(function(e){
		      return JSON.stringify(e);
                      Page.captureScreenshot(function (err, res) {
                              var buf = new Buffer(res.data, 'base64');
                              var imageFile = myArgs[3] + '.png'
                              fs.writeFileSync(imageFile, buf);
            });               
	    });
            fs.writeFileSync(traceFile, JSON.stringify(rawEvents, null, 0));
            console.log('Trace file: ' + traceFile);
            //console.log('You can open the trace file in DevTools Timeline panel. (Turn on experiment: Timeline tracing based JS profiler)\n')
            summary.report(summaryFile); // superfluous
            chrome.close();
        });
        
	//dataCOllected event send { "name": "value", "type": "array", "items": { "type": "object" } parameter as input
        Tracing.dataCollected(function(data){
            var events = data.value;
            rawEvents = rawEvents.concat(events);
	    // this is just extra but not really important
	    summary.onData(events);
        });

    }
}).on('error', function (e) {
    console.error('Cannot connect to Chrome', e);
});
