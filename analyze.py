#!/usr/bin/env python3.5
import os
import json
import shutil
import subprocess
import time
import logging
import coloredlogs
import trace_parser as tp
coloredlogs.install(level='INFO')

#_command = '/home/jnejati/PLTSpeed/analysis/trace_parser.py'
#logging.getLogger().setLevel(logging.INFO)
_experiment_dir = '/var/www/wprofx.cs.stonybrook.edu/public_html/WProfX/desktop_livetest'
_wprofx_graphs = '/var/www/wprofx.cs.stonybrook.edu/public_html/graphs'
_all_dirs = os.listdir(_experiment_dir)
_all_dirs.sort()
_exclude_list = []
working_dirs = [x for x in _all_dirs if x not in _exclude_list]
#working_dirs = ['www.statefarm.com']
for _site_dir in working_dirs:
    _site_dir = os.path.join(_experiment_dir, _site_dir)
    _runs = [x for x in os.listdir(_site_dir) if x.startswith('run')]
    for _run_no in _runs:
        _run_dir = os.path.join(_site_dir, _run_no)
        _analysis_dir = os.path.join(_run_dir, 'analysis')
        _summary_dir = os.path.join(_run_dir, 'summary')
        if os.path.isdir(_analysis_dir):
            for root, dirs, l_files in os.walk(_analysis_dir):
                for f in l_files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
        else:
            os.makedirs(_analysis_dir)
        _trace_dir = os.path.join(_run_dir, 'trace')
        for _file in os.listdir(_trace_dir):
            _trace_file = os.path.join(_trace_dir, _file)
            _output_file = os.path.join(_analysis_dir, _file.split('.trace')[0] + '.json')
            _waterfall_file = os.path.join(_analysis_dir, _file.split('.trace')[0] + '.html')
            for _f in os.listdir(_summary_dir):
                if _f.endswith('times'):
                    _times_file = os.path.join(_summary_dir, _f)
                    with open(_times_file) as _t:
                       for line in _t:
                            _time = json.loads(line)
            logging.info('Analyzing ' + _run_no + ' site: ' + _site_dir)
            #subprocess.call([_command, '-vvv',  '-t', _trace_file, '-o', _output_file, '-w', _waterfall_file], timeout = 300)
            trace = tp.Trace(_trace_file)
            _result, _start_ts, _cpu_times = trace.analyze()
            if not _result or not _start_ts or not _cpu_times:
                logging.warning('Incomplet trace file: ' + _file )
                continue
            _load_time = round(((float(_time['load'])* 1000000)  - float(_start_ts)) / 1000, 2)
            _result.insert(0, {'load': _load_time, 'cpu_time': _cpu_times['total_usecs']})
            trace.WriteJson(_output_file, _result)
            shutil.copy(_output_file, _wprofx_graphs)
