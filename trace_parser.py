#!/usr/bin/env python3.5
"""
Copyright 2016 Google Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-------------------------------------------------------------------------------------------------
Based on https://github.com/WPO-Foundation/webpagetest/blob/master/www/lib/trace/trace-parser.py
Copyright (c) 2005-2010, AOL, LLC.

All rights reserved.
"""
import collections
import copy
import gzip
import logging
import coloredlogs
import math
import os
import time
import sys
import csv
from urllib.parse import urldefrag
import networkx as nx
import matplotlib.pyplot as plt
import tldextract

# from graph_tool.all import *
# try a fast json parser if it is installed
from collections import defaultdict

from networkx.readwrite import json_graph

import waterfall_draw

try:
    import ujson as json
except:
    import json
coloredlogs.install(level='INFO')


########################################################################################################################
#   Trace processing
########################################################################################################################
class Trace():
    def __init__(self, trace):
        self.trace = trace
        self.thread_stack = {}
        self.ignore_threads = {}
        self.threads = {}
        self.user_timing = []
        self.event_names = {}
        self.event_name_lookup = {}
        self.scripts = None
        self.scripts_list = []
        self.scripts_lookup_url = {}
        self.scripts_lookup_id = {}
        self.timeline_events = []
        self.trace_events = []
        self.loading_trace_events = []
        self.network_trace_events = []
        self.netlog_trace_events = []
        self.painting_trace_events = []
        self.rendering_trace_events = []
        self.networks = {}
        self.networks_list = []
        self.networks_lookup_url = {}
        self.networks_lookup_id = {}
        self.loading = {}
        self.loading_list = []
        self.loading_lookup_url = {}
        self.loading_lookup_id = {}
        self.painting = {}
        self.painting_list = []
        self.rendering = {}
        self.rendering_list = []
        self.ordered = {}
        self.ordered_url_lookup = {}
        self.output = []
        self.last_activity = []
        self.all = []
        self.all_dict = {}
        self.all_modified = []
        self.all_modified_dict = {}
        self.deps_modified = []
        self.all_startTime_lookup = {}
        self.start_time = None
        self.end_time = None
        self.cpu = {'main_thread': None}
        self.feature_usage = None
        self.feature_usage_start_time = None
        self.netlog = {'bytes_in': 0, 'bytes_out': 0, 'ssl_bytes_in': 0, 'ssl_bytes_out': 0}
        self.G = nx.MultiDiGraph()
        self.deps = []
        self.deps_parent = {}
        self.critical_path = []
        self.visited = []
        self.fringe = []
        self.mark = {}
        self.javascript_type_list = ['application/x-javascript', 'application/javascript', 'application/ecmascript',
                                     'text/javascript', 'text/ecmascript', 'application/json', 'javascript/text']
        self.css_type_list = ['text/css', 'css/text']
        self.text_type_list = ['evalhtml', 'text/html', 'text/plain', 'text/xml']

    ########################################################################################################################
    #   Output Logging
    ########################################################################################################################
    def WriteJson(self, file, json_data):
        try:
            file_name, ext = os.path.splitext(file)
            if ext.lower() == '.gz':
                with gzip.open(file, 'wb') as f:
                    json.dump(json_data, f, indent=4)
            else:
                with open(file, 'w') as f:
                    json.dump(json_data, f, indent=4)
        except:
            logging.critical("Error writing to " + file)

    def WriteUserTiming(self, file):
        self.WriteJson(file, self.user_timing)

    def WriteCPUSlices(self, file):
        self.WriteJson(file, self.cpu)

    def WriteScriptTimings(self, file):
        if self.scripts is not None:
            self.WriteJson(file, self.scripts)

    def WriteFeatureUsage(self, file):
        self.WriteJson(file, self.feature_usage)

    def WriteNetlog(self, file):
        self.WriteJson(file, self.netlog)

    def WriteLoadinglog(self, file):
        self.WriteJson(file, self.loading)

    def WriteNetworklog(self, file):
        self.WriteJson(file, self.networks)

    def WritePaintinglog(self, file):
        self.WriteJson(file, self.painting)

    def WriteRenderinglog(self, file):
        self.WriteJson(file, self.rendering)

    def merge_dicts(self, *dict_args):
        """
        Given any number of dicts, shallow copy and merge into a new dict,
        precedence goes to key value pairs in latter dicts.
        """
        result = {}
        for dictionary in dict_args:
            result.update(dictionary)
        return result

    def WriteOutputlog_new(self, file=None, mode='main'):
        for _index, _value in enumerate(self.ordered):
            _url_group = _value[0]
            _node_Id_list = _value[1]
            _tmp_list = []
            for _nodeId in _node_Id_list:
                _tmp_dict = {}
                _tmp_merged_dict = {}
                if _nodeId.startswith('Network'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.networks_lookup_id[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)

                elif _nodeId.startswith('Load'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.loading[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
                elif _nodeId.startswith('Script'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.scripts_lookup_id[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
            self.output.append({'id': _url_group, 'objs': _tmp_list})

        _tmp_r_list = []
        for _index, _value in enumerate(self.rendering_list):
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_r_list.append(_tmp_merged_dict)

        _tmp_p_list = []
        for _index, _value in enumerate(self.painting_list):
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_p_list.append(_tmp_merged_dict)

        _tmp_rendering = {'id': 'Rendering', 'objs': _tmp_r_list}
        _tmp_painting = {'id': 'Painting', 'objs': _tmp_p_list}
        _tmp_deps = {'id': 'Deps', 'objs': self.deps}

        _tmp_netlog = {'id': 'Netlog', 'dns': self.netlog['dns'], 'sockets': self.netlog['sockets'],
                       'dnsTime': self.netlog['dnsTime'], 'sockets_bytes_in': self.netlog['bytes_in'],
                       'sockets_bytes_out': self.netlog['bytes_out'],
                       'ssl_sockets_bytes_out': self.netlog['ssl_bytes_out'],
                       'ssl_sockets_bytes_in': self.netlog['ssl_bytes_in']}
        _tmp_critical_path = {'criticalPath': self.critical_path}

        self.output.append(_tmp_rendering)
        self.output.append(_tmp_painting)
        self.output.append(_tmp_deps)
        self.output.append(_tmp_netlog)
        self.output.append(_tmp_critical_path)
        if mode == 'main':
            self.WriteJson(file, self.output)
        elif mode == 'lib':
            return self.output

    def WriteOutputlog(self, file=None, mode='main'):
        for _index, _value in enumerate(self.ordered):
            _url_group = _value[0]
            _node_Id_list = _value[1]
            _tmp_list = []
            for _nodeId in _node_Id_list:
                if _nodeId.startswith('Network'):
                    _tmp_list.append([_nodeId, self.networks_lookup_id[_nodeId]])
                elif _nodeId.startswith('Load'):
                    _tmp_list.append([_nodeId, self.loading[_nodeId]])
                elif _nodeId.startswith('Script'):
                    _tmp_list.append([_nodeId, self.scripts_lookup_id[_nodeId]])
            self.output.append({'id': _url_group, 'objs': _tmp_list})
        _tmp_rendering = {'id': 'Rendering', 'objs': self.rendering_list}
        _tmp_painting = {'id': 'Painting', 'objs': self.painting_list}
        _tmp_deps = {'id': 'Deps', 'objs': self.deps}
        _tmp_netlog = {'id': 'Netlog', 'dns': self.netlog['dns'], 'sockets': self.netlog['sockets'],
                       'dnsTime': self.netlog['dnsTime'], 'sockets_bytes_in': self.netlog['bytes_in'],
                       'sockets_bytes_out': self.netlog['bytes_out'],
                       'ssl_sockets_bytes_out': self.netlog['ssl_bytes_out'],
                       'ssl_sockets_bytes_in': self.netlog['ssl_bytes_in']}
        self.output.append(_tmp_rendering)
        self.output.append(_tmp_painting)
        self.output.append(_tmp_deps)
        self.output.append(_tmp_netlog)
        if mode == 'main':
            self.WriteJson(file, self.output)
        elif mode == 'lib':
            return self.output

    ########################################################################################################################
    #   Top-level processing
    ########################################################################################################################
    def Process_Loading_Render_Painting_Network(self):
        """f = None
        try:
            file_name, ext = os.path.splitext(trace)
            if ext.lower() == '.gz':
                f = gzip.open(trace, 'rb')
            else:
                f = open(trace, 'r')
            for line in f:
                try:
                    trace_event = json.loads(line.strip("[]\r\n\t ,"))
                    cat = trace_event['cat']
                    name = trace_event['name']
                    if (cat == 'devtools.timeline' and name == 'ParseHTML') or (
                                    cat == 'blink,devtools.timeline' and name == 'ParseAuthorStyleSheet'):
                        self.loading_trace_events.append(trace_event)
                    if (cat == 'disabled-by-default-devtools.timeline' or cat.find('devtools.timeline') >= 0) \
                            and name in ['CompositeLayers', 'Paint']:
                        self.painting_trace_events.append(trace_event)
                    if (cat == 'devtools.timeline' or cat.find('devtools.timeline') >= 0) \
                            and name in ['Layout', 'UpdateLayerTree', 'HitTest', 'RecalculateStyles']:
                        self.rendering_trace_events.append(trace_event)
                    if cat == 'devtools.timeline' and \
                            (name in ['ResourceSendRequest', 'ResourceReceiveResponse', 'ResourceReceivedData',
                                      'ResourceFinish']):
                        self.network_trace_events.append(trace_event)
                except:
                    raise
        except:
            logging.critical("Error processing trace " + trace)
            raise

        if f is not None:
            f.close()"""
        with open(self.trace, 'r') as content_file:
            content = content_file.read()
        trace_events = json.loads(content)
        for trace_event in trace_events:
            trace_event = json.loads(trace_event)
            try:
                cat = trace_event['cat']
                name = trace_event['name']
                if (cat == 'devtools.timeline' and name == 'ParseHTML') or (
                                cat == 'blink,devtools.timeline' and name == 'ParseAuthorStyleSheet'):
                    self.loading_trace_events.append(trace_event)
                ### removed to speed up plotting tests
                if (cat == 'disabled-by-default-devtools.timeline' or cat.find('devtools.timeline') >= 0) \
                        and name in ['CompositeLayers', 'Paint']:
                    self.painting_trace_events.append(trace_event)
                if (cat == 'devtools.timeline' or cat.find('devtools.timeline') >= 0) \
                        and name in ['Layout', 'UpdateLayerTree', 'HitTest', 'RecalculateStyles']:
                    self.rendering_trace_events.append(trace_event)
                if cat == 'devtools.timeline' and \
                        (name in ['ResourceSendRequest', 'ResourceReceiveResponse', 'ResourceReceivedData',
                                  'ResourceFinish']):
                    self.network_trace_events.append(trace_event)
                if cat == 'netlog':
                    self.netlog_trace_events.append(trace_event)
            except:
                raise

        self.network_trace_events.sort(key=lambda my_trace_event: my_trace_event['ts'])
        self.rendering_trace_events.sort(key=lambda my_trace_event: my_trace_event['ts'])
        self.loading_trace_events.sort(key=lambda my_trace_event: my_trace_event['ts'])
        self.painting_trace_events.sort(key=lambda my_trace_event: my_trace_event['ts'])
        self.netlog_trace_events.sort(key=lambda my_trace_event: my_trace_event['ts'])
        # Convert the source event id to hex if one exists in netlog
        self.convertIdtoHex(self.netlog_trace_events)

    def convertIdtoHex(self, _trace):
        for trace_event in _trace:
            if 'args' in trace_event and 'id' in trace_event and 'name' in trace_event and 'source_type' in trace_event[
                'args']:
                # Convert the source event id to hex if one exists
                if 'params' in trace_event['args'] and 'source_dependency' in trace_event['args']['params'] and 'id' in \
                        trace_event['args']['params']['source_dependency']:
                    dependency_id = int(trace_event['args']['params']['source_dependency']['id'])
                    trace_event['args']['params']['source_dependency']['id'] = '0x%x' % dependency_id
        return _trace

    def Process(self):
        with open(self.trace, 'r') as content_file:
            content = content_file.read()
        trace_events = json.loads(content)
        for trace_event in trace_events:
            trace_event = json.loads(trace_event)
            try:
                self.FilterTraceEvent(trace_event)
            except:
                raise
        """f = None
        line_mode = False
        self.__init__()
        try:
            file_name, ext = os.path.splitext(trace)
            if ext.lower() == '.gz':
                f = gzip.open(trace, 'rb')
            else:
                f = open(trace, 'r')
            for line in f:
                try:
                    trace_event = json.loads(line.strip("[]\r\n\t ,"))
                    if not line_mode and 'traceEvents' in trace_event:
                        for sub_event in trace_event['traceEvents']:
                            self.FilterTraceEvent(sub_event)
                    else:
                        line_mode = True
                        self.FilterTraceEvent(trace_event)
                except:
                    pass
        except:
            logging.critical("Error processing trace " + trace)

        if f is not None:
            f.close()"""

        self.ProcessTraceEvents()

    def FilterTraceEvent(self, trace_event):
        cat = trace_event['cat']
        if cat == 'toplevel' or cat == 'ipc,toplevel':
            return
        if cat == 'devtools.timeline' or \
                        cat.find('devtools.timeline') >= 0 or \
                        cat.find('blink.feature_usage') >= 0 or \
                        cat.find('blink.user_timing') >= 0:
            self.trace_events.append(trace_event)

    def ProcessTraceEvents(self):
        # sort the raw trace events by timestamp and then process them
        if len(self.trace_events):
            self.trace_events.sort(key=lambda trace_event: trace_event['ts'])
            for trace_event in self.trace_events:
                self.ProcessTraceEvent(trace_event)
            self.trace_events = []

        # Do the post-processing on timeline events
        self.ProcessTimelineEvents()

    def ProcessTraceEvent(self, trace_event):
        cat = trace_event['cat']
        if cat == 'devtools.timeline' or cat.find('devtools.timeline') >= 0:
            self.ProcessTimelineTraceEvent(trace_event)
            # elif cat.find('blink.feature_usage') >= 0:
            # self.ProcessFeatureUsageEvent(trace_event)
        elif cat.find('blink.user_timing') >= 0:
            self.user_timing.append(trace_event)
            # Netlog support is still in progress
            # elif cat.find('netlog') >= 0:
            #  self.ProcessNetlogEvent(trace_event)

    ########################################################################################################################
    #   Timeline
    ########################################################################################################################
    """
    Chrome: Loading, Scripting, Rendering, Painting
    Loading: ParseHTML, ParseAuthorStyleSheet
    Scripting: FunctionCall, EvaluateScript, V8.Execute, v8.compile, MajorGC, MinorGC, GCEvent
    Rendering: Layout, RecalculateStyle, UpdateLayerTree, HitTest
    Painting: CompositeLayers, Paint

    Notes:
    - A hit test is how a contact (mouse/touch) event is checked to see what it "hit" in the DOM.
    --------------------bigrig----------------------
    Toplevel: domContentLoaded, loadTime, firstPaint
    1- ParseHTML
    2- js: FunctionCall, EvaluateScript, V8.Execute, MajorGC, MinorGC, GCEvent v8.compile
    3- Styles: UpdateLayoutTree, RecalculateStyles, ParseAuthorStyleSheet
    4- UpdateLayerTree
    5- Layout
    6- Paint
    7- RasterTask, Rasterize
    8- CompositeLayers
    """

    # ["toplevel", "blink.console", "disabled-by-default-devtools.timeline", "devtools.timeline", "disabled-by-default-devtools.timeline.frame", "devtools.timeline.frame", "v8.execute", "disabled-by-default-blink.feature_usage", "blink.user_timing", "disabled-by-default-devtools.timeline.stack", "devtools.timeline.stack"]

    ########################################################################################################################
    #   Netlog
    ########################################################################################################################
    def ProcessNetlogEvent(self, netlog_trace_events):
        for trace_event in netlog_trace_events:
            if 'args' in trace_event and 'id' in trace_event and 'name' in trace_event and 'source_type' in trace_event[
                'args']:
                if trace_event['name'] == 'DNS_TRANSACTION':
                    self.ProcessNetlogDnsEvent(trace_event)
                if trace_event['args']['source_type'] == 'SOCKET':
                    if trace_event['name'].startswith('SSL'):
                        self.ProcessNetlogSslSocketEvent(trace_event)
                    else:
                        self.ProcessNetlogSocketEvent(trace_event)
                """if trace_event['args']['source_type'] == 'HTTP2_SESSION':
                    self.ProcessNetlogHTTP2SessionEvent(trace_event)"""
        self.TotalDnsTime()

    def TotalDnsTime(self):
        _total_time = 0
        if 'dns' in self.netlog:
            for _id in self.netlog['dns']:
                if 'dnsStart' in self.netlog['dns'][_id] and 'dnsEnd' in self.netlog['dns'][_id]:
                    _total_time += self.netlog['dns'][_id]['dnsEnd'] - self.netlog['dns'][_id]['dnsStart']
            if 'dnsTime' not in self.netlog:
                self.netlog['dnsTime'] = {}
            self.netlog['dnsTime'] = _total_time
        else:
            self.netlog['dns'] = {}
            self.netlog['dnsTime'] = -1

    def ProcessNetlogDnsEvent(self, s):
        if 'dns' not in self.netlog:
            self.netlog['dns'] = {}
        if s['id'] not in self.netlog['dns']:
            self.netlog['dns'][s['id']] = {}
        if s['name'] == 'DNS_TRANSACTION' and 'params' in s['args']:
            if s['ph'] == 'b':
                self.netlog['dns'][s['id']]['hostname'] = s['args']['params']['hostname']
                self.netlog['dns'][s['id']]['dnsStart'] = (s['ts'] - self.start_time) / 1000
            elif s['ph'] == 'e':
                if not 'net_error' in s['args']['params']:
                    self.netlog['dns'][s['id']]['dnsEnd'] = (s['ts'] - self.start_time) / 1000
                elif s['id'] in self.netlog['dns']:
                    del self.netlog['dns'][s['id']]

    def ProcessNetlogSocketEvent(self, s):
        if 'sockets' not in self.netlog:
            self.netlog['sockets'] = {}
        if s['id'] not in self.netlog['sockets']:
            self.netlog['sockets'][s['id']] = {'bytes_in': 0, 'bytes_out': 0}
        if s['name'] == 'SOCKET_BYTES_RECEIVED' and 'params' in s['args'] and 'byte_count' in s['args']['params']:
            self.netlog['sockets'][s['id']]['bytes_in'] += s['args']['params']['byte_count']
            self.netlog['bytes_in'] += s['args']['params']['byte_count']
        if s['name'] == 'SOCKET_BYTES_SENT' and 'params' in s['args'] and 'byte_count' in s['args']['params']:
            self.netlog['sockets'][s['id']]['bytes_out'] += s['args']['params']['byte_count']
            self.netlog['bytes_out'] += s['args']['params']['byte_count']

    def ProcessNetlogSslSocketEvent(self, s):
        if 'ssl_sockets' not in self.netlog:
            self.netlog['ssl_sockets'] = {}
        if s['id'] not in self.netlog['ssl_sockets']:
            self.netlog['ssl_sockets'][s['id']] = {'ssl_bytes_in': 0, 'ssl_bytes_out': 0}
        if s['name'] == 'SSL_SOCKET_BYTES_RECEIVED' and 'params' in s['args'] and 'byte_count' in s['args'][
            'params']:
            self.netlog['ssl_sockets'][s['id']]['ssl_bytes_in'] += s['args']['params']['byte_count']
            self.netlog['ssl_bytes_in'] += s['args']['params']['byte_count']
        if s['name'] == 'SSL_SOCKET_BYTES_SENT' and 'params' in s['args'] and 'byte_count' in s['args']['params']:
            self.netlog['ssl_sockets'][s['id']]['ssl_bytes_out'] += s['args']['params']['byte_count']
            self.netlog['ssl_bytes_out'] += s['args']['params']['byte_count']

    def ProcessNetlogHTTP2SessionEvent(self, s):
        if 'params' in s['args'] and 'stream_id' in s['args']['params']:
            if 'http2' not in self.netlog:
                self.netlog['http2'] = {'bytes_in': 0, 'bytes_out': 0}
            if s['id'] not in self.netlog['http2']:
                self.netlog['http2'][s['id']] = {'bytes_in': 0, 'bytes_out': 0, 'streams': {}}
            stream = '{0:d}'.format(s['args']['params']['stream_id'])
            if stream not in self.netlog['http2'][s['id']]['streams']:
                self.netlog['http2'][s['id']]['streams'][stream] = {'start': s['tts'], 'end': s['tts'], 'bytes_in': 0,
                                                                    'bytes_out': 0}
            if s['tts'] > self.netlog['http2'][s['id']]['streams'][stream]['end']:
                self.netlog['http2'][s['id']]['streams'][stream]['end'] = s['tts']

        if s['name'] == 'HTTP2_SESSION_SEND_HEADERS' and 'params' in s['args']:
            if 'request' not in self.netlog['http2'][s['id']]['streams'][stream]:
                self.netlog['http2'][s['id']]['streams'][stream]['request'] = {}
            if 'headers' in s['args']['params']:
                self.netlog['http2'][s['id']]['streams'][stream]['request']['headers'] = s['args']['params']['headers']
            if 'parent_stream_id' in s['args']['params']:
                self.netlog['http2'][s['id']]['streams'][stream]['request']['parent_stream_id'] = s['args']['params'][
                    'parent_stream_id']
            if 'exclusive' in s['args']['params']:
                self.netlog['http2'][s['id']]['streams'][stream]['request']['exclusive'] = s['args']['params'][
                    'exclusive']
            if 'priority' in s['args']['params']:
                self.netlog['http2'][s['id']]['streams'][stream]['request']['priority'] = s['args']['params'][
                    'priority']

        if s['name'] == 'HTTP2_SESSION_RECV_HEADERS' and 'params' in s['args']:
            if 'first_byte' not in self.netlog['http2'][s['id']]['streams'][stream]:
                self.netlog['http2'][s['id']]['streams'][stream]['first_byte'] = s['tts']
            if 'response' not in self.netlog['http2'][s['id']]['streams'][stream]:
                self.netlog['http2'][s['id']]['streams'][stream]['response'] = {}
            if 'headers' in s['args']['params']:
                self.netlog['http2'][s['id']]['response']['streams'][stream]['headers'] = s['args']['params']['headers']

        if s['name'] == 'HTTP2_SESSION_RECV_DATA' and 'params' in s['args'] and 'size' in s['args']['params']:
            if 'first_byte' not in self.netlog['http2'][s['id']]['streams'][stream]:
                self.netlog['http2'][s['id']]['streams'][stream]['first_byte'] = s['tts']
            self.netlog['http2'][s['id']]['streams'][stream]['bytes_in'] += s['args']['params']['size']
            self.netlog['http2'][s['id']]['bytes_in'] += s['args']['params']['size']

    def ProcessNetworkEvents(self, network_trace_events):
        for net_trace in network_trace_events:
            _request_id = net_trace['args']['data']['requestId']
            if _request_id not in self.networks:
                self.networks[_request_id] = {}
            if net_trace['name'] == 'ResourceSendRequest':
                _url = net_trace['args']['data']['url']
                _startTime = net_trace['ts']
                self.networks[_request_id]['url'] = _url
                self.networks[_request_id]['startTime'] = (_startTime - self.start_time) / 1000

                if 'stackTrace' in net_trace['args']['data']:
                    _script_url = net_trace['args']['data']['stackTrace'][0]['url']
                    self.networks[_request_id]['fromScript'] = _script_url
                else:
                    self.networks[_request_id]['fromScript'] = 'Null'

            elif net_trace['name'] == 'ResourceReceiveResponse':
                _statusCode = net_trace['args']['data']['statusCode']
                _mimeType = net_trace['args']['data']['mimeType']
                _responseReceivedTime = net_trace['ts']

                self.networks[_request_id]['statusCode'] = _statusCode
                self.networks[_request_id]['responseReceivedTime'] = (_responseReceivedTime - self.start_time) / 1000
                self.networks[_request_id]['mimeType'] = _mimeType

            elif net_trace['name'] == 'ResourceReceivedData':
                _encodedDataLength = net_trace['args']['data']['encodedDataLength']
                if _encodedDataLength != 0 or 'transferSize' not in self.networks[_request_id]:
                    self.networks[_request_id]['transferSize'] = _encodedDataLength

            elif net_trace['name'] == 'ResourceFinish':
                _endTime = net_trace['ts']
                _didFail = net_trace['args']['data']['didFail']
                if not _didFail:
                    self.networks[_request_id]['endTime'] = (_endTime - self.start_time) / 1000
                else:
                    self.networks.pop(_request_id, None)
            else:
                raise Exception('Unknown network name in net_trace')

    def is_balanced(self, a_list):
        my_list = copy.deepcopy(a_list)
        t_stack = []
        for i in range(len(my_list)):
            if my_list[i]['ph'] == 'B':
                t_stack.append('B')
            elif my_list[i]['ph'] == 'E':
                t_stack.pop()
        if len(t_stack) == 0:
            return True
        return False

    def merge_events(self, aList):
        if len(aList) > 2:
            return [[aList[0], aList[-1]], [aList[1:-1]]]
        else:
            return [[aList[0], aList[-1]]]

    def ProcessLoadingEvents(self, loading_trace_events):
        load_list = []
        tmp_stack = []
        for loading_event in loading_trace_events:
            loading_event['ts'] = (loading_event['ts'] - self.start_time) / 1000
            if loading_event['ph'] == 'B' or loading_event['ph'] == 'E':
                if loading_event['ph'] == 'B':
                    tmp_stack.append(loading_event)
                elif loading_event['ph'] == 'E':
                    if not len(tmp_stack) == 0:
                        tmp_stack.append(loading_event)
                    else:
                        logging.warning('E detected without any B')
                        continue
                if self.is_balanced(tmp_stack):
                    load_list.append(self.merge_events(tmp_stack))
                    tmp_stack = []
            ###
            # ParseAuthorStyleSheet
            ###
            elif loading_event[
                'ph'] == 'X':  # The ts parameter indicate the time of the start of the 'complete (X)' event.
                loading_event['dur'] /= 1000
                load_list.append([[loading_event]])

        for i in range(len(load_list)):
            self.loading['Loading_' + str(i)] = {}
            self.loading['Loading_' + str(i)]['fromScript'] = None
            self.loading['Loading_' + str(i)]['styleSheetUrl'] = None
            self.loading['Loading_' + str(i)]['url'] = None

            _name = load_list[i][0][0]['name']
            self.loading['Loading_' + str(i)]['name'] = _name
            _startTime = load_list[i][0][0]['ts']
            self.loading['Loading_' + str(i)]['startTime'] = _startTime

            if load_list[i][0][0]['ph'] == 'B':
                _endTime = load_list[i][0][1]['ts']
                self.loading['Loading_' + str(i)]['endTime'] = _endTime
                _pageURL = load_list[i][0][0]['args']['beginData']['url']
                self.loading['Loading_' + str(i)]['url'] = _pageURL
                if 'stackTrace' in load_list[i][0][0]['args']['beginData']:
                    _scriptUrL = load_list[i][0][0]['args']['beginData']['stackTrace'][0]['url']
                    self.loading['Loading_' + str(i)]['fromScript'] = _scriptUrL
            elif load_list[i][0][0]['ph'] == 'X':
                _duration = load_list[i][0][0]['dur']
                _endTime = _startTime + _duration
                self.loading['Loading_' + str(i)]['endTime'] = _endTime
                if 'data' in load_list[i][0][0]['args']:
                    _styleSheetUrl = load_list[i][0][0]['args']['data']['styleSheetUrl']
                    self.loading['Loading_' + str(i)]['styleSheetUrl'] = _styleSheetUrl
        self.loading = collections.OrderedDict(sorted(self.loading.items(), key=lambda t: int(t[0].split('_')[1])))

    def ProcessPaintingEvents(self, painting_trace_events):
        paint_list = []
        tmp_stack = []
        for paint_event in painting_trace_events:
            paint_event['ts'] = (paint_event['ts'] - self.start_time) / 1000
            if paint_event['ph'] == 'B' or paint_event['ph'] == 'E':
                if paint_event['ph'] == 'B':
                    tmp_stack.append(paint_event)
                elif paint_event['ph'] == 'E':
                    if not len(tmp_stack) == 0:
                        tmp_stack.append(paint_event)
                    else:
                        logging.warning('E detected without any B')
                        continue
                if self.is_balanced(tmp_stack):
                    paint_list.append(self.merge_events(tmp_stack))
                    tmp_stack = []
            ###
            # Paint
            ###
            elif paint_event[
                'ph'] == 'X':  # The ts parameter indicate the time of the start of the 'complete (X)' event.
                if 'dur' in paint_event:
                    paint_event['dur'] /= 1000
                else:
                    paint_event['dur'] = 0
                paint_list.append([[paint_event]])
        for i in range(len(paint_list)):
            self.painting['Painting_' + str(i)] = {}
            _startTime = paint_list[i][0][0]['ts']
            self.painting['Painting_' + str(i)]['startTime'] = _startTime
            _name = paint_list[i][0][0]['name']
            self.painting['Painting_' + str(i)]['name'] = _name
            if paint_list[i][0][0]['ph'] == 'B':
                _endTime = paint_list[i][0][1]['ts']
                self.painting['Painting_' + str(i)]['endTime'] = _endTime
                if 'args' in paint_list[i][0][0]:
                    if 'layerTreeId' in paint_list[i][0][0]['args']:
                        _layerTreeId = paint_list[i][0][0]['args']['layerTreeId']
                    else:
                        _layerTreeId = None
                    self.painting['Painting_' + str(i)]['layerTreeId'] = _layerTreeId
            elif paint_list[i][0][0]['ph'] == 'X':
                _duration = paint_list[i][0][0]['dur']
                _endTime = _startTime + _duration
                self.painting['Painting_' + str(i)]['endTime'] = _endTime

        self.painting = collections.OrderedDict(sorted(self.painting.items(), key=lambda t: int(t[0].split('_')[1])))

    def ProcessRenderingEvents(self, rendering_trace_events):
        render_list = []
        tmp_stack = []
        # main_pid = self.cpu['main_thread'].split(':')[0]
        # main_tid = self.cpu['main_thread'].split(':')[1]

        for render_event in rendering_trace_events:
            render_event['ts'] = (render_event['ts'] - self.start_time) / 1000
            ###
            # Layout, RecalculateStyle, HitTest
            ###
            if render_event['ph'] == 'B' or render_event['ph'] == 'E':
                if render_event['ph'] == 'B':
                    tmp_stack.append(render_event)
                elif render_event['ph'] == 'E':
                    if not len(tmp_stack) == 0:
                        tmp_stack.append(render_event)
                    else:
                        logging.warning('E detected without any B in: ' + render_event['name'])
                        continue
                if self.is_balanced(tmp_stack):
                    render_list.append(self.merge_events(tmp_stack))
                    tmp_stack = []
                    ###
                    # UpdateLayerTree
                    ###
            elif render_event[
                'ph'] == 'X':  # The ts parameter indicate the time of the start of the 'complete (X)' event.
                if 'dur' in render_event:
                    render_event['dur'] /= 1000
                    render_list.append([[render_event]])

        for i in range(len(render_list)):
            self.rendering['Rendering_' + str(i)] = {}
            _startTime = render_list[i][0][0]['ts']
            self.rendering['Rendering_' + str(i)]['startTime'] = _startTime
            _name = render_list[i][0][0]['name']
            self.rendering['Rendering_' + str(i)]['name'] = _name
            if render_list[i][0][0]['ph'] == 'B':
                _endTime = render_list[i][0][1]['ts']
                self.rendering['Rendering_' + str(i)]['endTime'] = _endTime
                ###
                # {"pid":20396,"tid":775,"ts":1390025575932,"ph":"B","cat":"devtools.timeline","name":"Layout",
                # "args":{"beginData":{"dirtyObjects":25,"frame":"0x2b8722801e08","partialLayout":false,"totalObjects":241}},"tts":2462518},
                ###
            elif render_list[i][0][0]['ph'] == 'X':
                _duration = render_list[i][0][0]['dur']
                _endTime = _startTime + _duration
                self.rendering['Rendering_' + str(i)]['endTime'] = _endTime

        self.rendering = collections.OrderedDict(sorted(self.rendering.items(), key=lambda t: int(t[0].split('_')[1])))

    def ProcessTimelineTraceEvent(self, trace_event):
        thread = '{0}:{1}'.format(trace_event['pid'], trace_event['tid'])
        # Keep track of the main thread
        if self.cpu['main_thread'] is None and trace_event[
            'name'] == 'ResourceSendRequest' and 'args' in trace_event and \
                        'data' in trace_event['args'] and 'url' in trace_event['args']['data']:
            if trace_event['args']['data']['url'][:21] == 'http://127.0.0.1:8888':
                self.ignore_threads[thread] = True
            else:
                if thread not in self.threads:
                    self.threads[thread] = {}
                if self.start_time is None or trace_event['ts'] < self.start_time:
                    self.start_time = trace_event['ts']
                self.cpu['main_thread'] = thread
                if 'dur' not in trace_event:
                    trace_event['dur'] = 1

        # Make sure each thread has a numerical ID
        if self.cpu['main_thread'] is not None and thread not in self.threads and thread not in self.ignore_threads and \
                        trace_event['name'] != 'Program':
            self.threads[thread] = {}

        # Build timeline events on a stack. 'B' begins an event, 'E' ends an event
        if (thread in self.threads and ('dur' in trace_event or trace_event['ph'] == 'B' or trace_event['ph'] == 'E')):
            trace_event['thread'] = self.threads[thread]
            if thread not in self.thread_stack:
                self.thread_stack[thread] = []
            if trace_event['name'] not in self.event_names:
                self.event_names[trace_event['name']] = len(self.event_names)
                self.event_name_lookup[self.event_names[trace_event['name']]] = trace_event['name']
            if trace_event['name'] not in self.threads[thread]:
                self.threads[thread][trace_event['name']] = self.event_names[trace_event['name']]
            e = None
            if trace_event['ph'] == 'E':
                if len(self.thread_stack[thread]) > 0:
                    e = self.thread_stack[thread].pop()
                    if e['n'] == self.event_names[trace_event['name']]:
                        e['e'] = trace_event['ts']
            else:
                e = {'t': thread, 'n': self.event_names[trace_event['name']], 's': trace_event['ts']}
                if (trace_event['name'] == 'EvaluateScript' or trace_event['name'] == 'v8.compile' or trace_event[
                    'name'] == 'v8.parseOnBackground') \
                        and 'args' in trace_event and 'data' in trace_event['args'] and 'url' in trace_event['args'][
                    'data'] and \
                        trace_event['args']['data']['url'].startswith('http'):
                    e['js'] = trace_event['args']['data']['url']
                if trace_event['name'] == 'FunctionCall' and 'args' in trace_event and 'data' in trace_event['args'] and \
                                'scriptName' in trace_event['args']['data'] and trace_event['args']['data'][
                    'scriptName'].startswith('http'):
                    e['js'] = trace_event['args']['data']['scriptName']
                if trace_event['ph'] == 'B':
                    self.thread_stack[thread].append(e)
                    e = None
                elif 'dur' in trace_event:
                    e['e'] = e['s'] + trace_event['dur']

            if e is not None and 'e' in e and e['s'] >= self.start_time and e['e'] >= e['s']:
                if self.end_time is None or e['e'] > self.end_time:
                    self.end_time = e['e']
                # attach it to a parent event if there is one
                if len(self.thread_stack[thread]) > 0:
                    parent = self.thread_stack[thread].pop()
                    if 'c' not in parent:
                        parent['c'] = []
                    parent['c'].append(e)
                    self.thread_stack[thread].append(parent)
                else:
                    self.timeline_events.append(e)

    def ProcessTimelineEvents(self):
        if len(self.timeline_events) and self.end_time > self.start_time:
            # Figure out how big each slice should be in usecs. Size it to a power of 10 where we have at least 2000 slices
            exp = 0
            last_exp = 0
            slice_count = self.end_time - self.start_time
            while slice_count > 2000:
                last_exp = exp
                exp += 1
                slice_count = int(math.ceil(float(self.end_time - self.start_time) / float(pow(10, exp))))
            self.cpu['total_usecs'] = self.end_time - self.start_time
            self.cpu['slice_usecs'] = int(pow(10, last_exp))
            slice_count = int(math.ceil(float(self.end_time - self.start_time) / float(self.cpu['slice_usecs'])))

            # Create the empty time slices for all of the threads
            self.cpu['slices'] = {}
            for thread in self.threads.keys():
                self.cpu['slices'][thread] = {'total': [0.0] * slice_count}
                for name in self.threads[thread].keys():
                    self.cpu['slices'][thread][name] = [0.0] * slice_count

            # Go through all of the timeline events recursively and account for the time they consumed
            for timeline_event in self.timeline_events:
                self.ProcessTimelineEvent(timeline_event, None)

            # Go through all of the fractional times and convert the float fractional times to integer usecs
            for thread in self.cpu['slices'].keys():
                del self.cpu['slices'][thread]['total']
                for name in self.cpu['slices'][thread].keys():
                    for slice in range(len(self.cpu['slices'][thread][name])):
                        self.cpu['slices'][thread][name][slice] = \
                            int(self.cpu['slices'][thread][name][slice] * self.cpu['slice_usecs'])

    def ProcessTimelineEvent(self, timeline_event, parent):
        start = timeline_event['s'] - self.start_time
        end = timeline_event['e'] - self.start_time
        if end > start:
            elapsed = end - start
            thread = timeline_event['t']
            name = self.event_name_lookup[timeline_event['n']]
            if 'js' in timeline_event:
                script = timeline_event['js']
                s = start / 1000.0
                e = end / 1000.0
                if self.scripts is None:
                    self.scripts = {}
                if 'main_thread' not in self.scripts and 'main_thread' in self.cpu:
                    self.scripts['main_thread'] = self.cpu['main_thread']
                if thread not in self.scripts:
                    self.scripts[thread] = {}
                if script not in self.scripts[thread]:
                    self.scripts[thread][script] = {}
                if name not in self.scripts[thread][script]:
                    self.scripts[thread][script][name] = []
                new_duration = True
                if len(self.scripts[thread][script][name]):
                    for period in self.scripts[thread][script][name]:
                        if s >= period[0] and e <= period[1]:
                            new_duration = False
                            break
                if new_duration:
                    self.scripts[thread][script][name].append([s, e])

            slice_usecs = self.cpu['slice_usecs']
            first_slice = int(float(start) / float(slice_usecs))
            last_slice = int(float(end) / float(slice_usecs))
            for slice_number in range(first_slice, last_slice + 1):
                slice_start = slice_number * slice_usecs
                slice_end = slice_start + slice_usecs
                used_start = max(slice_start, start)
                used_end = min(slice_end, end)
                slice_elapsed = used_end - used_start
                self.AdjustTimelineSlice(thread, slice_number, name, parent, slice_elapsed)

            # Recursively process any child events
            if 'c' in timeline_event:
                for child in timeline_event['c']:
                    self.ProcessTimelineEvent(child, name)

    # Add the time to the given slice and subtract the time from a parent event
    def AdjustTimelineSlice(self, thread, slice_number, name, parent, elapsed):
        try:
            # Don't bother adjusting if both the current event and parent are the same category
            # since they would just cancel each other out.
            if name != parent:
                fraction = min(1.0, float(elapsed) / float(self.cpu['slice_usecs']))
                self.cpu['slices'][thread][name][slice_number] += fraction
                self.cpu['slices'][thread]['total'][slice_number] += fraction
                if parent is not None and self.cpu['slices'][thread][parent][slice_number] >= fraction:
                    self.cpu['slices'][thread][parent][slice_number] -= fraction
                    self.cpu['slices'][thread]['total'][slice_number] -= fraction
                # Make sure we didn't exceed 100% in this slice
                self.cpu['slices'][thread][name][slice_number] = min(1.0,
                                                                     self.cpu['slices'][thread][name][slice_number])

                # make sure we don't exceed 100% for any slot
                if self.cpu['slices'][thread]['total'][slice_number] > 1.0:
                    available = max(0.0, 1.0 - fraction)
                    for slice_name in self.cpu['slices'][thread].keys():
                        if slice_name != name:
                            self.cpu['slices'][thread][slice_name][slice_number] = \
                                min(self.cpu['slices'][thread][slice_name][slice_number], available)
                            available = max(0.0, available - self.cpu['slices'][thread][slice_name][slice_number])
                    self.cpu['slices'][thread]['total'][slice_number] = min(1.0, max(0.0, 1.0 - available))
        except:
            pass

            ########################################################################################################################
            # Dependency processing:
            # Sort based on startTime and endTime
            # Edges --> deps
            # What-if analysis (critical path changes based on object duration change)
            ########################################################################################################################

    def find_download0(self):
        download_0 = None
        parse_0 = None
        for obj in self.all:
            # print(self.all)
            if 'Network' in obj[0]:
                if obj[1]['mimeType'] == 'text/html':  # and obj[1]['url'].startswith('http'):
                    download_0 = obj  # Wprof style naming
                    break
        if download_0:
            for obj in self.all:
                if 'Loading' in obj[0]:
                    if obj[1]['name'] == 'ParseHTML' and obj[1]['url'] == download_0[1][
                        'url']:  # and obj[1]['url'].startswith('http'):
                        parse_0 = obj
                        break
            if parse_0:
                return (download_0, parse_0)
            else:
                return False, False
        else:
            return False, False

    def find_load_time(self):
        pass

    def find_DomContentLoaded_time(self):
        pass

    def find_firstPaint_time(self):
        pass

    def find_ttbf(self):
        pass

    def find_cp_max_end(self, aList):
        _max = -10
        _max_id = None
        for _tup in aList:
            if _tup[1] > _max:
                _max = _tup[1]
                _max_id = _tup[0]
        return _max_id


    def find_critical_path_mod(self, source):
        self.critical_path += [source]
        if source in self.deps_parent:
            source = self.find_cp_max_end(self.deps_parent_mod[source])
            return self.find_critical_path_mod(source)
        else:
            return

    def find_critical_path(self, source):
        self.critical_path += [source]
        if source in self.deps_parent:
            source = self.find_cp_max_end(self.deps_parent[source])
            return self.find_critical_path(source)
        else:
            return

    def find_critical_path_old(self, source, download_0=None):
        # this version uses max prev trigger time. Need to consider duration.
        # Maybe we should switch from critical path (Longest endTimes) to the least idle critical path (Longest durations)
        # prev_list = self.G.in_edges(source, data=True)
        # OR calculate Load, the last activity might be after Load
        self.critical_path += [source]
        if source in self.deps_parent:
            for prev in self.deps_parent[source]:
                if not prev in self.critical_path:
                    self.find_critical_path = self.find_critical_path(prev, download_0)
            return self.find_critical_path
        else:
            return

    def sort_by_startTime(self):
        max_net_time = [['', 0]]
        max_load_time = [['', 0]]
        max_script_time = [['', 0]]
        # sort all processed events by startTime
        self.networks_list = [[_id, net_dict] for _id, net_dict in self.networks.items()
                              if ('startTime' in net_dict and net_dict['startTime'] >= 0) and
                              ('endTime' in net_dict and net_dict['endTime'] >= 0)]
        self.networks_list = sorted(self.networks_list, key=lambda tup: tup[1]['startTime'])
        for i in range(len(self.networks_list)):
            temp_net_list = ['Networking_' + str(i), {'id': self.networks_list[i][0]}]
            temp_net_list[1]['startTime'] = self.networks_list[i][1]['startTime']
            temp_net_list[1]['endTime'] = self.networks_list[i][1]['endTime']
            if temp_net_list[1]['endTime'] > max_net_time[0][1]:
                max_net_time[0][1] = temp_net_list[1]['endTime']
                max_net_time[0][0] = 'Networking_' + str(i)
            temp_net_list[1]['mimeType'] = self.networks_list[i][1]['mimeType']
            temp_net_list[1]['url'] = self.networks_list[i][1]['url']
            temp_net_list[1]['fromScript'] = self.networks_list[i][1]['fromScript']
            if 'transferSize' in self.networks_list[i][1]:
                temp_net_list[1]['transferSize'] = self.networks_list[i][1]['transferSize']
            temp_net_list[1]['responseReceivedTime'] = self.networks_list[i][1]['responseReceivedTime']
            temp_net_list[1]['statusCode'] = self.networks_list[i][1]['statusCode']
            self.networks_list[i] = temp_net_list
            unfragmented_url = urldefrag(self.networks_list[i][1]['url'])[0]
            if "localhost.localdomain" in unfragmented_url:
                unfragmented_url = unfragmented_url.replace('localhost.localdomain/', '')
            if not unfragmented_url in self.networks_lookup_url:
                self.networks_lookup_url[unfragmented_url] = [self.networks_list[i][0]]
            else:
                self.networks_lookup_url[unfragmented_url].append(self.networks_list[i][0])
            self.networks_lookup_id['Networking_' + str(i)] = temp_net_list[1]
            temp_net_list = []
        self.loading_list = [[_id, load_dict] for _id, load_dict in self.loading.items()
                             if ('startTime' in load_dict and load_dict['startTime'] >= 0) and
                             ('endTime' in load_dict and load_dict['endTime'] >= 0)]

        for t_id, t_dict in self.loading_list:
            unfragmented_url = urldefrag(t_dict['url'])[0]
            if unfragmented_url and 'localhost.localdomain' in unfragmented_url:
                unfragmented_url = unfragmented_url.replace('localhost.localdomain/', '')
            if not unfragmented_url in self.loading_lookup_url:
                self.loading_lookup_url[unfragmented_url] = [t_id]
            else:
                self.loading_lookup_url[unfragmented_url].append(t_id)
            self.loading_lookup_id[t_id] = t_dict
            if t_dict['endTime'] > max_load_time[0][1]:
                max_load_time[0][1] = t_dict['endTime']
                max_load_time[0][0] = t_id
        self.loading_list = sorted(self.loading_list, key=lambda tup: tup[1]['startTime'])
        _main_thread = self.scripts['main_thread']
        scripts2 = self.scripts[str(_main_thread)]
        for _id, script_dict in scripts2.items():
            if ('EvaluateScript' in script_dict and len(script_dict['EvaluateScript'])) > 0:
                for j in range(len(script_dict['EvaluateScript'])):
                    self.scripts_list.append([_id, {'startTime': script_dict['EvaluateScript'][j][0],
                                                    'endTime': script_dict['EvaluateScript'][j][1]}])

            """if ('EvaluateScript' in script_dict and 'startTime' in script_dict['EvaluateScript'] and
                        script_dict['EvaluateScript']['startTime'] >= 0) and \
                    ('endTime' in script_dict['EvaluateScript'] and script_dict['EvaluateScript']['endTime'] >= 0):
                self.scripts_list.append([_id, script_dict['EvaluateScript']])"""

        """self.scripts_list = [[_id, script_dict['EvaluateScript']] for _id, script_dict in scripts2.items()
                         if ('startTime' in script_dict['EvaluateScript'] and script_dict['EvaluateScript'][
            'startTime'] > 0) and ('endTime' in script_dict['EvaluateScript'] and script_dict['EvaluateScript'][
            'endTime'] > 0)]"""
        self.scripts_list = sorted(self.scripts_list, key=lambda tup: tup[1]['startTime'])

        for i in range(len(self.scripts_list)):
            self.scripts_list[i] = ['Scripting_' + str(i), {'url': self.scripts_list[i][0],
                                                            'startTime': self.scripts_list[i][1]['startTime'],
                                                            'endTime': self.scripts_list[i][1]['endTime']}]
            unfragmented_url = urldefrag(self.scripts_list[i][1]['url'])[0]
            if "localhost.localdomain" in unfragmented_url:
                unfragmented_url = unfragmented_url.replace('localhost.localdomain/', '')
            if not unfragmented_url in self.scripts_lookup_url:
                self.scripts_lookup_url[unfragmented_url] = ['Scripting_' + str(i)]
            else:
                self.scripts_lookup_url[unfragmented_url].append('Scripting_' + str(i))

            # self.scripts_lookup_url[unfragmented_url] = 'Scripting_' + str(i)
            self.scripts_lookup_id['Scripting_' + str(i)] = self.scripts_list[i][1]
            if self.scripts_list[i][1]['endTime'] > max_script_time[0][1]:
                max_script_time[0][1] = self.scripts_list[i][1]['endTime']
                max_script_time[0][0] = 'Scripting_' + str(i)

        self.rendering_list = [[_id, render_dict] for _id, render_dict in self.rendering.items()
                               if ('startTime' in render_dict and render_dict['startTime'] >= 0) and
                               ('endTime' in render_dict and render_dict['endTime'] >= 0)]
        self.rendering_list = sorted(self.rendering_list, key=lambda tup: tup[1]['startTime'])

        self.painting_list = [[_id, paint_dict] for _id, paint_dict in self.painting.items()
                              if ('startTime' in paint_dict and paint_dict['startTime'] >= 0) and
                              ('endTime' in paint_dict and paint_dict['endTime'] >= 0)]
        self.painting_list = sorted(self.painting_list, key=lambda tup: tup[1]['startTime'])

        self.all = self.networks_list + self.loading_list + self.scripts_list + self.rendering_list + self.painting_list
        self.all = sorted(self.all, key=lambda tup: tup[1]['startTime'])
        for obj in self.all:
            self.all_startTime_lookup[obj[0]] = obj[1]['startTime']
        self.all_modified = copy.deepcopy(self.all)
        for _item in self.all:
            self.all_dict[_item[0]] = _item[1]
        for _item in self.all_modified:
            self.all_modified_dict[_item[0]] = _item[1]
        _tmp_merged = max_net_time + max_load_time + max_script_time
        self.last_activity = sorted(_tmp_merged, key=lambda tup: tup[1], reverse=True)
        # print(_tmp_merged)
        # print('Last activity: ' + str(self.last_activity[0]))

    def order_layout(self):
        i = 0
        for net_obj in self.networks_list:
            # if not net_obj[1]['mimeType'].startswith('image'):
            self.ordered.setdefault(urldefrag(net_obj[1]['url'])[0], []).append(net_obj[0])
            if len(self.ordered[urldefrag(net_obj[1]['url'])[0]]) == 1:
                self.ordered_url_lookup[urldefrag(net_obj[1]['url'])[0]] = i
                i += 1

        for script_obj in self.scripts_list:
            self.ordered.setdefault(urldefrag(script_obj[1]['url'])[0], []).append(script_obj[0])
            if len(self.ordered[urldefrag(script_obj[1]['url'])[0]]) == 1:
                self.ordered_url_lookup[urldefrag(script_obj[1]['url'])[0]] = i
                i += 1

        for load_obj in self.loading_list:
            if load_obj[1]['name'] == 'ParseHTML':
                self.ordered.setdefault(urldefrag(load_obj[1]['url'])[0], []).append(load_obj[0])
                if len(self.ordered[urldefrag(load_obj[1]['url'])[0]]) == 1:
                    self.ordered_url_lookup[urldefrag(load_obj[1]['url'])[0]] = i
                    i += 1

            elif load_obj[1]['name'] == 'ParseAuthorStyleSheet':
                self.ordered.setdefault(urldefrag(load_obj[1]['styleSheetUrl'])[0], []).append(load_obj[0])
                if len(self.ordered[urldefrag(load_obj[1]['styleSheetUrl'])[0]]) == 1:
                    self.ordered_url_lookup[urldefrag(load_obj[1]['styleSheetUrl'])[0]] = i
                    i += 1
        self.ordered = sorted(self.ordered.items(), key=lambda e: self.all_startTime_lookup[e[1][0]])

    def merge_dicts(self, *dict_args):
        """
        Given any number of dicts, shallow copy and merge into a new dict,
        precedence goes to key value pairs in latter dicts.
        """
        result = {}
        for dictionary in dict_args:
            result.update(dictionary)
        return result

    def draw_waterfall(self, _resJson, _outf):
        n_lookup = copy.deepcopy(self.networks_lookup_id)
        s_lookup = copy.deepcopy(self.scripts_lookup_id)
        l_lookup = copy.deepcopy(self.loading_lookup_id)
        _lookup_dict = self.merge_dicts(n_lookup, s_lookup, l_lookup)
        _order_lookup = {}
        for _index, _item in enumerate(self.ordered):
            for _sitem in _item[1]:
                _order_lookup[_sitem] = _index

        _plot = waterfall_draw.DrawWaterfall(_resJson, _outf, _lookup_dict, _order_lookup)
        #_plot = waterfall_draw.DrawWaterfall(_resJson, _outf, _lookup_dict, _order_lookup, self.all_modified_dict)
        # _plot.draw_from_json()
        _plot.draw_from_json_new()
        _plot.draw_critical_path(self.critical_path)
        #_plot.draw_all_dependency()
        _plot.showPlot()

    def CreateGraph(self):
        download_0, parse_0 = self.find_download0()
        if not download_0 or not parse_0:
            return False
        # print('download_0: ', download_0)
        # print('parse_0: ', parse_0)
        self.G.graph['download_0'] = download_0[0]
        self.G.graph['parse_0'] = parse_0[0]

        for obj in self.all:
            if obj[0].startswith('Networking') or obj[0].startswith('Loading') or obj[0].startswith('Scripting'):
                self.G.add_node(obj[0], obj[1])
        return True

    def edge_start(self, e1, s2):
        if e1 < s2:
            return e1, -1
        else:
            return s2, s2

    def toGephiCsv(self, _site):
        # _eHeader = ('source', 'target', 'Type')
        _edges = self.G.edges()
        # _edges.insert(0, _eHeader)
        _nHeader = ('id', 'label')
        _nodes = self.G.nodes()
        _nodes.insert(0, _nHeader)
        with open(_site + '_edges.csv', 'w', newline='') as myfile:
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerows(_edges)

        with open(_site + '_nodes.csv', 'w', newline='') as myfile2:
            wr2 = csv.writer(myfile2, quoting=csv.QUOTE_ALL)
            wr2.writerow(_nodes)

    def find_url(self, _url, activitiy_data, _type):
        activity_startTime = activitiy_data['startTime']
        activity_endTime = activitiy_data['endTime']
        selected = ['', float('inf')]
        if _type == 'network':
            for net_id in self.networks_lookup_url[_url]:
                net_startTime = self.networks_list[int(net_id.split('_')[1])][1]['startTime']
                net_endTime = self.networks_list[int(net_id.split('_')[1])][1]['endTime']
                if activity_startTime > net_startTime and activity_endTime > net_endTime:
                    diff = abs(activity_startTime - net_endTime)
                    if diff < selected[1]:
                        selected = [net_id, diff]
            return selected[0]
        elif _type == 'script':
            # print(self.scripts_lookup_url[_url])
            for s_id in self.scripts_lookup_url[_url]:
                _startTime = self.scripts_list[int(s_id.split('_')[1])][1]['startTime']
                _endTime = self.scripts_list[int(s_id.split('_')[1])][1]['endTime']
                # print(_startTime, _endTime)
                if activity_startTime > _startTime:
                    diff = abs(activity_startTime - _endTime)
                    if diff < selected[1]:
                        selected = [s_id, diff]
            if selected[0] == '':
                print('script', self.scripts_lookup_url[_url], _startTime, _endTime, _url, activitiy_data)
                exit()
            return selected[0]

    # Find latest parse HTML before activity
    def find_parse_id(self, activitiy_data):
        activity_startTime = activitiy_data['startTime']
        selected = ['', float('inf')]
        for loadings in self.loading_list:
            load_id = loadings[0]
            load_data = loadings[1]
            load_name = load_data['name']
            if load_name.startswith('ParseHTML'):
                _startTime = load_data['startTime']
                _endTime = load_data['endTime']
                _url = load_data['url']
                if _url not in ['', 'about:blank'] and activity_startTime > _startTime:
                    diff = abs(activity_startTime - _endTime)
                    if diff < selected[1]:
                        selected = [load_id, diff]
        if selected[0] in ['', None]:
            print(selected[0], activitiy_data)
            exit()
        return selected[0]

    # Find latest scripting before parsing
    def find_scripting_id(self, activitiy_data):
        activity_startTime = activitiy_data['startTime']
        selected = ['', float('inf')]
        for scriptings in self.scripts_list:
            script_id = scriptings[0]
            script_data = scriptings[1]
            _startTime = script_data['startTime']
            _endTime = script_data['endTime']
            _url = script_data['url']
            if _url not in ['', 'about:blank'] and activity_startTime > _startTime:
                diff = abs(activity_startTime - _endTime)
                if diff < selected[1]:
                    selected = [script_id, diff]
        if selected[0] in ['', None]:
            print(selected[0], activitiy_data)
            return None
        return selected[0]

    def dependency(self):
        if not self.CreateGraph():
            return False
        _download0Id = self.G.graph['download_0']
        if not _download0Id:
            return False
        _parse0Id = self.G.graph['parse_0']
        a2_startTime, a1_triggered = self.edge_start(self.G.node[_download0Id]['endTime'],
                                                     self.G.node[_parse0Id]['startTime'])
        self.G.add_edge(_download0Id, _parse0Id,
                        startTime=a2_startTime,
                        endTime=self.G.node[_parse0Id]['startTime'])
        self.deps.append({'time': a1_triggered, 'a1': _download0Id, 'a2': _parse0Id})
        if a1_triggered == -1:
            a1_triggered = self.G.node[_download0Id]['endTime']
        self.deps_parent.setdefault(_parse0Id, []).append((_download0Id, a1_triggered))
        for obj in self.all:
            _nodeId = obj[0]
            _nodeData = obj[1]
            ###
            #  Add find_url like scheme for netwoorks which are null
            ###
            if _nodeId.startswith('Networking') or _nodeId.startswith('Loading') or _nodeId.startswith('Scripting'):
                if _nodeId.startswith('Networking'):
                    if _nodeData['fromScript'] in ['Null', None, ''] and _nodeData['startTime'] > \
                            self.G.node[_parse0Id][
                                'startTime']:
                        _parseID = self.find_parse_id(_nodeData)
                        if _parseID in ['', None]:
                            _parseID = _parse0Id
                        a2_startTime, a1_triggered = self.edge_start(self.G.node[_parseID]['endTime'],
                                                                     self.G.node[_nodeId]['startTime'])
                        self.G.add_edge(_parseID, _nodeId,
                                        startTime=a2_startTime,
                                        endTime=self.G.node[_nodeId]['startTime'])
                        self.deps.append({'time': a1_triggered, 'a1': _parseID, 'a2': _nodeId})
                        if a1_triggered == -1:
                            a1_triggered = self.G.node[_parseID]['endTime']
                        self.deps_parent.setdefault(_nodeId, []).append((_parseID, a1_triggered))
                    elif _nodeData['fromScript'] not in ['Null', None, '']:
                        if len(self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]]) <= 1:
                            _script_nodeId = self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]][0]
                        else:
                            _script_nodeId = self.find_url(urldefrag(_nodeData['fromScript'])[0], _nodeData, 'script')
                        # _script_nodeId = self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]]
                        _script_nodeData = self.scripts_list[int(_script_nodeId.split('_')[1])][1]
                        # There is a js before _nodeId
                        if _script_nodeData['startTime'] < self.G.node[_nodeId]['startTime']:
                            a2_startTime, a1_triggered = self.edge_start(self.G.node[_script_nodeId]['endTime'],
                                                                         self.G.node[_nodeId]['startTime'])
                            self.G.add_edge(_script_nodeId, _nodeId,
                                            startTime=a2_startTime,
                                            endTime=self.G.node[_nodeId]['startTime'])
                            self.deps.append({'time': a1_triggered, 'a1': _script_nodeId, 'a2': _nodeId})
                            if a1_triggered == -1:
                                a1_triggered = self.G.node[_script_nodeId]['endTime']
                            self.deps_parent.setdefault(_nodeId, []).append((_script_nodeId, a1_triggered))

                elif _nodeId.startswith('Scripting'):
                    # find related networking for each js eval.
                    if len(self.networks_lookup_url[urldefrag(_nodeData['url'])[0]]) <= 1:
                        _netowrk_nodeId = self.networks_lookup_url[urldefrag(_nodeData['url'])[0]][0]
                    else:
                        _netowrk_nodeId = self.find_url(urldefrag(_nodeData['url'])[0], _nodeData, 'network')
                    _netowrk_nodeData = self.networks_list[int(_netowrk_nodeId.split('_')[1])][1]
                    if _netowrk_nodeData['startTime'] < self.G.node[_nodeId]['startTime']:
                        a2_startTime, a1_triggered = self.edge_start(self.G.node[_netowrk_nodeId]['endTime'],
                                                                     self.G.node[_nodeId]['startTime'])
                        self.G.add_edge(_netowrk_nodeId, _nodeId,
                                        startTime=a2_startTime,
                                        endTime=self.G.node[_nodeId]['startTime'])
                        self.deps.append({'time': a1_triggered, 'a1': _netowrk_nodeId, 'a2': _nodeId})
                        if a1_triggered == -1:
                            a1_triggered = self.G.node[_netowrk_nodeId]['endTime']
                        self.deps_parent.setdefault(_nodeId, []).append((_netowrk_nodeId, a1_triggered))

                elif _nodeId.startswith('Loading'):
                    if _nodeData['name'] == 'ParseAuthorStyleSheet':
                        try:
                            if len(self.networks_lookup_url[urldefrag(_nodeData['styleSheetUrl'])[0]]) <= 1:
                                _netowrk_nodeId = self.networks_lookup_url[urldefrag(_nodeData['styleSheetUrl'])[0]][0]
                            else:
                                _netowrk_nodeId = self.find_url(urldefrag(_nodeData['styleSheetUrl'])[0], _nodeData,
                                                                'network')
                        except Exception as e:
                            print(e)
                            continue
                        _netowrk_nodeData = self.networks_list[int(_netowrk_nodeId.split('_')[1])][1]
                        if _netowrk_nodeData['startTime'] < self.G.node[_nodeId]['startTime']:
                            a2_startTime, a1_triggered = self.edge_start(self.G.node[_netowrk_nodeId]['endTime'],
                                                                         self.G.node[_nodeId]['startTime'])
                            self.G.add_edge(_netowrk_nodeId, _nodeId,
                                            startTime=a2_startTime,
                                            endTime=self.G.node[_nodeId]['startTime'])
                            self.deps.append({'time': a1_triggered, 'a1': _netowrk_nodeId, 'a2': _nodeId})
                            if a1_triggered == -1:
                                a1_triggered = self.G.node[_netowrk_nodeId]['endTime']
                            self.deps_parent.setdefault(_nodeId, []).append((_netowrk_nodeId, a1_triggered))

                    elif _nodeData['name'] == 'ParseHTML' and _nodeData['fromScript'] in ['Null', None, '']:
                        ### TODO: Javad
                        # We are currently skipping about:blanks which occur before parse_0
                        # Update: no need if a clean start happens in testbed.
                        ###
                        if _nodeData['startTime'] > self.G.node[_parse0Id]['startTime'] and not _nodeData['url'] == '':
                            if len(self.networks_lookup_url[urldefrag(_nodeData['url'])[0]]) <= 1:
                                _netowrk_nodeId = self.networks_lookup_url[urldefrag(_nodeData['url'])[0]][0]
                            else:
                                _netowrk_nodeId = self.find_url(urldefrag(_nodeData['url'])[0], _nodeData, 'network')
                            _netowrk_nodeData = self.networks_list[int(_netowrk_nodeId.split('_')[1])][1]
                            a2_startTime, a1_triggered = self.edge_start(self.G.node[_netowrk_nodeId]['endTime'],
                                                                         self.G.node[_nodeId]['startTime'])
                            self.G.add_edge(_netowrk_nodeId, _nodeId,
                                            startTime=a2_startTime,
                                            endTime=self.G.node[_nodeId]['startTime'])
                            self.deps.append({'time': a1_triggered, 'a1': _netowrk_nodeId, 'a2': _nodeId})
                            if a1_triggered == -1:
                                a1_triggered = self.G.node[_netowrk_nodeId]['endTime']
                            self.deps_parent.setdefault(_nodeId, []).append((_netowrk_nodeId, a1_triggered))
                            ###
                            # find latest scripting too
                            ###
                            _script_nodeId = self.find_scripting_id(_nodeData)
                            if _script_nodeId is not None:
                                a2_startTime, a1_triggered = self.edge_start(self.G.node[_script_nodeId]['endTime'],
                                                                             self.G.node[_nodeId]['startTime'])
                                self.G.add_edge(_script_nodeId, _nodeId,
                                                startTime=a2_startTime,
                                                endTime=self.G.node[_nodeId]['startTime'])
                                self.deps.append({'time': a1_triggered, 'a1': _script_nodeId, 'a2': _nodeId})
                                if a1_triggered == -1:
                                    a1_triggered = self.G.node[_script_nodeId]['endTime']
                                self.deps_parent.setdefault(_nodeId, []).append((_script_nodeId, a1_triggered))

                            ###
                            # Find latest parsHTML too
                            ###
                            _parseID = self.find_parse_id(_nodeData)
                            if _parseID in ['', None]:
                                _parseID = _parse0Id
                            a2_startTime, a1_triggered = self.edge_start(self.G.node[_parseID]['endTime'],
                                                                         self.G.node[_nodeId]['startTime'])
                            self.G.add_edge(_parseID, _nodeId,
                                            startTime=a2_startTime,
                                            endTime=self.G.node[_nodeId]['startTime'])
                            self.deps.append({'time': a1_triggered, 'a1': _parseID, 'a2': _nodeId})
                            if a1_triggered == -1:
                                a1_triggered = self.G.node[_parseID]['endTime']
                            self.deps_parent.setdefault(_nodeId, []).append((_parseID, a1_triggered))

                        else:
                            pass

                    elif _nodeData['name'] == 'ParseHTML' and _nodeData['fromScript'] not in ['Null', None, '']:
                        # _script_nodeId = self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]]
                        if len(self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]]) <= 1:
                            _script_nodeId = self.scripts_lookup_url[urldefrag(_nodeData['fromScript'])[0]][0]
                        else:
                            _script_nodeId = self.find_url(urldefrag(_nodeData['fromScript'])[0], _nodeData, 'script')
                        _script_nodeData = self.scripts_list[int(_script_nodeId.split('_')[1])][1]
                        # There is a js before _nodeId
                        if _script_nodeData['startTime'] < self.G.node[_nodeId]['startTime']:
                            a2_startTime, a1_triggered = self.edge_start(self.G.node[_script_nodeId]['endTime'],
                                                                         self.G.node[_nodeId]['startTime'])
                            self.G.add_edge(_script_nodeId, _nodeId,
                                            startTime=a2_startTime,
                                            endTime=self.G.node[_nodeId]['startTime'])
                            self.deps.append({'time': a1_triggered, 'a1': _script_nodeId, 'a2': _nodeId})
                            if a1_triggered == -1:
                                a1_triggered = self.G.node[_script_nodeId]['endTime']
                            self.deps_parent.setdefault(_nodeId, []).append((_script_nodeId, a1_triggered))
        self.deps_modified = copy.deepcopy(self.deps)
        return True
        # print(self.G.nodes(data=True))
        # self.toGephiCsv('zdnet')
        # simpleNetworkx(self.G)

        # 1- find first html download and call it download_0 //WProf Style
        # 2- for all objects after download_0:
        #    - ** if it is a text/html download and fromScript: fromScript--> Networking_x then:
        #       there could be a loading (ParseHTML) (fast.cbsi... in zdnet) with the same fromScript URL and
        #        a Scripting with URL startswith the Networking URL and finishes before ParseHTML event.
        #
        #    - if it is an image and does not have a fromScript: loading_0--> Networking_x
        #        elif fromscript is a js: fromScript --> Networking_x
        #
        #    - if it is a CSS download and no fromScript: loading_0--> Networking_x
        #    - if it is a CSS download and fromScript: fromScript--> Networking_x
        #
        #    - if it is a Loading (HTML and CSS):
        #       - if ParseHTML and no fromScript, find corrosponding Networking (url match): Networking_x --> ParseHTML
        #       - if ParseHTML and fromScript, same as **
        #       - if ParseAuthorStyleSheet:  and Networking_x --> ParseAuthorStylesSheet
        #
        #    - if it is a script download and no fromScript  loading_0--> Networking_x
        #    - if it is a scripting download and fromScript: fromScript--> Networking_x
        #    - if it is a Scripting EvalScript Networking_x --> Scripting or
        #    - It can be from a ParseHTML called fromScript which is actually a script (same as **)
        #
        #
        #

    ###################################################################################################
    #  What-if analysis --begins
    ###################################################################################################
    def WriteOutputlog_modified(self, file=None, mode='main'):
        self._outputModified = copy.deepcopy(self.output)
        for _index, _value in enumerate(self.ordered):
            _url_group = _value[0]
            _node_Id_list = _value[1]
            _tmp_list = []
            for _nodeId in _node_Id_list:
                _tmp_dict = {}
                if _nodeId.startswith('Network'):
                    _tmp_dict['activityId'] = _nodeId
                    ### Add new stime and etime here.
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.networks_lookup_id[_nodeId])
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']

                    _tmp_list.append(_tmp_merged_dict)
                elif _nodeId.startswith('Load'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.loading[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']
                elif _nodeId.startswith('Script'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.scripts_lookup_id[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']
            self.output.append({'id': _url_group, 'objs': _tmp_list})

        _tmp_r_list = []
        for _index, _value in enumerate(self.rendering_list):
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_r_list.append(_tmp_merged_dict)

        _tmp_p_list = []
        for _index, _value in enumerate(self.painting_list):
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_p_list.append(_tmp_merged_dict)

        _tmp_rendering = {'id': 'Rendering', 'objs': _tmp_r_list}
        _tmp_painting = {'id': 'Painting', 'objs': _tmp_r_list}
        _tmp_deps = {'id': 'Deps', 'objs': self.deps_modified}

        _tmp_netlog = {'id': 'Netlog', 'dns': self.netlog['dns'], 'sockets': self.netlog['sockets'],
                       'dnsTime': self.netlog['dnsTime'], 'sockets_bytes_in': self.netlog['bytes_in'],
                       'sockets_bytes_out': self.netlog['bytes_out'],
                       'ssl_sockets_bytes_out': self.netlog['ssl_bytes_out'],
                       'ssl_sockets_bytes_in': self.netlog['ssl_bytes_in']}
        _tmp_critical_path = {'criticalPath': self.critical_path}

        self.output.append(_tmp_rendering)
        self.output.append(_tmp_painting)
        self.output.append(_tmp_deps)
        self.output.append(_tmp_netlog)
        self.output.append(_tmp_critical_path)
        if mode == 'main':
            self.WriteJson(file, self.output)
        elif mode == 'lib':
            return self.output

    def update_nodeData(self, _nodeId, _delta, _function):
        self.all_modified_dict[_nodeId]['startTime'] -= _delta
        self.all_modified_dict[_nodeId]['endTime'] -= _delta
        self.all_modified_dict[_nodeId]['endTime'] = _function(_nodeId)

    def _compression(self, _nodeId):
        _startTime = self.all_modified_dict[_nodeId]['startTime']
        _endTime = self.all_modified_dict[_nodeId]['endTime']
        if _nodeId.startswith('Networking') and _nodeId not in self.mark:
            _mimeType = self.all_modified_dict[_nodeId]['mimeType']
            #_compressable = self.javascript_type_list + self.css_type_list + self.text_type_list
            _compressable = self.javascript_type_list
            if _mimeType in _compressable:
                return _startTime + ((_endTime - _startTime) / 15.7)
        return _endTime

    def _caching(self, _nodeId):
        _startTime = self.all_modified_dict[_nodeId]['startTime']
        _endTime = self.all_modified_dict[_nodeId]['endTime']
        if _nodeId.startswith('Networking') and _nodeId not in self.mark:
            _mimeType = self.all_modified_dict[_nodeId]['mimeType']
            if _mimeType.startswith('image'):
                print(_nodeId)
                return _startTime + 2
        return _endTime

    def isAd(self, _url):
        if _url is  None or 'testbed01' in _url:
            return False
        ads_domain = ['doubleclick.net', 'googlesyndication.com']
        s = tldextract.extract(_url)
        _domain = s.domain
        _suffix = s.suffix
        _subdomain = s.subdomain
        _d = _domain + '.' + _suffix
        print(_d)
        if _d in ads_domain:
            return True
        return False
        # ExtractResult(subdomain='www', domain='worldbank', suffix='org.kg')

    def WriteOutputlog_ads(self, file=None, mode='main'):
        adS_id_list = []
        self._outputModified = copy.deepcopy(self.output)
        for _index, _value in enumerate(self.ordered):
            _url_group = _value[0]
            _node_Id_list = _value[1]
            _tmp_list = []
            for _nodeId in _node_Id_list:
                _tmp_dict = {}
                _tmp_dict['url'] = self.all_modified_dict[_nodeId]['url']
                if self.isAd(_tmp_dict['url']) or _nodeId in ['Networking_9', 'Loading_7']:
                    adS_id_list.append(_nodeId)
                    continue
                if _nodeId.startswith('Network'):
                    _tmp_dict['activityId'] = _nodeId
                    ### Add new stime and etime here.
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.networks_lookup_id[_nodeId])
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']

                    _tmp_list.append(_tmp_merged_dict)
                elif _nodeId.startswith('Load'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.loading[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']
                elif _nodeId.startswith('Script'):
                    _tmp_dict['activityId'] = _nodeId
                    _tmp_merged_dict = self.merge_dicts(_tmp_dict, self.scripts_lookup_id[_nodeId])
                    _tmp_list.append(_tmp_merged_dict)
                    _tmp_merged_dict['startTime'] = self.all_modified_dict[_nodeId]['startTime']
                    _tmp_merged_dict['endTime'] = self.all_modified_dict[_nodeId]['endTime']
            self.output.append({'id': _url_group, 'objs': _tmp_list})

        _tmp_r_list = []
        for _index, _value in enumerate(self.rendering_list):
            continue
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_r_list.append(_tmp_merged_dict)

        _tmp_p_list = []
        for _index, _value in enumerate(self.painting_list):
            continue
            _nodeId = _value[0]
            _tmp_dict['activityId'] = _nodeId
            _nodeData = _value[1]
            _tmp_merged_dict = self.merge_dicts(_tmp_dict, _nodeData)
            _tmp_p_list.append(_tmp_merged_dict)

        _tmp_rendering = {'id': 'Rendering', 'objs': _tmp_r_list}
        _tmp_painting = {'id': 'Painting', 'objs': _tmp_r_list}
        for i, _obj in enumerate(self.deps_modified):
            if _obj['a1'] in adS_id_list or _obj['a1'] in adS_id_list:
                del self.deps_modified[i]
        _tmp_deps = {'id': 'Deps', 'objs': self.deps_modified}

        _tmp_netlog = {'id': 'Netlog', 'dns': self.netlog['dns'], 'sockets': self.netlog['sockets'],
                       'dnsTime': self.netlog['dnsTime'], 'sockets_bytes_in': self.netlog['bytes_in'],
                       'sockets_bytes_out': self.netlog['bytes_out'],
                       'ssl_sockets_bytes_out': self.netlog['ssl_bytes_out'],
                       'ssl_sockets_bytes_in': self.netlog['ssl_bytes_in']}
        _tmp_critical_path = {'criticalPath': self.critical_path}

        self.output.append(_tmp_rendering)
        self.output.append(_tmp_painting)
        self.output.append(_tmp_deps)
        self.output.append(_tmp_netlog)
        self.output.append(_tmp_critical_path)
        #self.critical_path = ['Networking_0', 'Loading_0', 'Networking_3', 'Scripting_0', 'Loading_2', 'Networking_5']
        if mode == 'main':
            self.WriteJson(file, self.output)
        elif mode == 'lib':
            return self.output

    def update_nodeData(self, _nodeId, _delta, _function):
        self.all_modified_dict[_nodeId]['startTime'] -= _delta
        self.all_modified_dict[_nodeId]['endTime'] -= _delta
        self.all_modified_dict[_nodeId]['endTime'] = _function(_nodeId)

    def _compression(self, _nodeId):
        _startTime = self.all_modified_dict[_nodeId]['startTime']
        _endTime = self.all_modified_dict[_nodeId]['endTime']
        if _nodeId.startswith('Networking') and _nodeId not in self.mark:
            _mimeType = self.all_modified_dict[_nodeId]['mimeType']
            #_compressable = self.javascript_type_list + self.css_type_list + self.text_type_list
            _compressable = self.javascript_type_list
            if _mimeType in _compressable:
                return _startTime + ((_endTime - _startTime) / 15.7)
        return _endTime

    def _caching(self, _nodeId):
        _startTime = self.all_modified_dict[_nodeId]['startTime']
        _endTime = self.all_modified_dict[_nodeId]['endTime']
        if _nodeId.startswith('Networking') and _nodeId not in self.mark:
            _mimeType = self.all_modified_dict[_nodeId]['mimeType']
            if _mimeType.startswith('image'):
                print(_nodeId)
                return _startTime + 2
        return _endTime


    def shift_time(self, _nodeId, _function):
        if _nodeId not in self.deps_parent:  # Orphans
            self.all_modified_dict[_nodeId]['endTime'] = _function(_nodeId)
            self.mark[_nodeId] = True
            return
        for _parentId in self.deps_parent[_nodeId]:
            if _parentId[0] not in self.mark:
                self.shift_time(_parentId[0], _function)
        _maxEndTime = float('-inf')
        for _parentId in self.deps_parent[_nodeId]:
            _endTime = _function(_parentId[0])
            #print(_parentId[0], _endTime, self.all_dict[_parentId[0]]['endTime'] )
            if _endTime > _maxEndTime:
                _maxEndTime = _endTime
                _delta = self.all_dict[_parentId[0]]['endTime'] - _endTime
        self.update_nodeData(_nodeId, _delta, _function)
        self.mark[_nodeId] = True

    def shift_deps(self):
        self.deps_parent_mod = {}
        for _nodeId, _parents in self.deps_parent.items():
            for _pTuple in _parents:
                _pId = _pTuple[0]
                _newEndTime = self.all_modified_dict[_pId]['endTime']
                self.deps_parent_mod.setdefault(_nodeId, []).append((_pId, _newEndTime))
        for idx, _deps in enumerate(self.deps_modified):
            if not _deps['time'] == -1:
                _orig_startTime = self.all_dict[_deps['a1']]['startTime']
                _orig_endTime = self.all_dict[_deps['a1']]['endTime']
                _mod_startTime = self.all_modified_dict[_deps['a1']]['startTime']
                _mod_endTime = self.all_modified_dict[_deps['a1']]['endTime']
                _ratio = (_mod_endTime - _mod_startTime)/(_orig_endTime - _orig_startTime)
                _orig_Offset = _deps['time'] - _orig_startTime
                _a1Time = _mod_startTime + (_orig_Offset * _ratio)
                #print(_deps['a1'], _deps['a2'], _orig_startTime, _orig_endTime, _mod_startTime, _mod_endTime,_ratio, _orig_Offset, _deps['time'], _a1Time )
                if _a1Time < self.all_modified_dict[_deps['a2']]['startTime']:
                    _a1Time = -1
                self.deps_modified[idx] = {'a1': _deps['a1'], 'time': _a1Time, 'a2': _deps['a2']}

    ###################################################################################################
    #  What-if analysis --ends
    ###################################################################################################

    def analyze(self):
        logging.info('Analyzing: ' + str(self.trace))
        self.Process()
        logging.info('start_ts: ' + str(self.start_time))
        self.Process_Loading_Render_Painting_Network()
        self.ProcessNetworkEvents(self.network_trace_events)
        self.ProcessLoadingEvents(self.loading_trace_events)
        self.ProcessRenderingEvents(self.rendering_trace_events)
        self.ProcessPaintingEvents(self.painting_trace_events)
        self.ProcessNetlogEvent(self.netlog_trace_events)
        self.sort_by_startTime()
        if not self.dependency():
            return False, False, False
        self.order_layout()
        #self.adjust_time_compressed()
        ###
        # Do the same untill all are marked
        #keep track of marked
        ###
        _nodeId_list = [x[0] for x in self.all_modified]
        _nodeId_list.reverse()
        for _nodeId in _nodeId_list:
            if _nodeId not in self.mark:
                #self.shift_time(_nodeId, self._compression)
                self.shift_time(_nodeId, self._compression)
        self.shift_deps()
        download_0, parse_0 = self.find_download0()
        #self.find_critical_path(self.last_activity[0][0])  # , download_0[0])
        self.find_critical_path_mod(self.last_activity[0][0])  # , download_0[0])
        self.critical_path.reverse()
        print('Critical Path: ' + str(self.critical_path))
        return self.WriteOutputlog_new(mode='lib'), self.start_time, self.cpu


########################################################################################################################
#   Main Entry Point
########################################################################################################################
def main():
    #_trace_file = '/Users/jnejati/PycharmProjects/wpt/traces/1_testbed01.trace' # uncompressed mutli imgs
    _trace_file = '/Users/jnejati/PycharmProjects/wpt/traces/1_testbed01_jsbig_uncompgood3g.trace'
    _trace_file = '/Users/jnejati/PycharmProjects/wpt/traces/1_testbed01_jsbig_compgood3g.trace'
    _trace_file = '/Users/jnejati/PycharmProjects/wpt/traces/0_www.cnn.com.trace'


    trace = Trace(_trace_file)
    _result, _start_ts, _cpu_times = trace.analyze()
    """for t in trace.networks_list:
        if 'dcmads.js' in t[1]['url']:
        #if 'dcmads.js' in t:
            print(t)
    exit()"""
    _output_file = './results/cnn_cold_new.json'
    trace.WriteJson(_output_file, _result)
    trace.draw_waterfall(_output_file, 'cnn_new.html')


if '__main__' == __name__:
    #  import cProfile
    #  cProfile.run('main()', None, 2)
    main()
