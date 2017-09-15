#!/usr/bin/env python3.5
__author__ = 'jnejati'

#import experiments
import json
import signal
import pickle
import webDnsSetupMobile
import network_emulator
import os
import convert
from urllib.parse import urlparse
import time
#import modifications as modify
#from bs4 import BeautifulSoup
import urllib.request
import urllib.response
import io
import gzip
import subprocess
import logging
#import coloredlogs
#coloredlogs.install(level='INFO')
import timeit

def _change_resolv_conf():
    RESOLV_CONF = '/etc/resolv.conf'
    with open (RESOLV_CONF, 'w') as _f:
        _f.write('nameserver         127.0.0.1\n')


def main():
    start = timeit.default_timer()
    input_file = 'mixed-mobile.txt'
    archive_dir = '/home/jnejati/PLTSpeed/record/archive-m/'
    config_file = '/home/jnejati/PLTSpeed/confs/netProfiles.json'
    _change_resolv_conf()
    with open(config_file, 'r') as f:
        net_profile = json.load(f)[0]
        _path =  os.path.join('/home/jnejati/PLTSpeed', net_profile['device_type'] + '_' + net_profile['name'])
        webDnsSetupMobile.clear_folder(_path)
    with open('/home/jnejati/PLTSpeed/res/' + input_file) as _sites:
        for _site in _sites:
            #_chrome_process = subprocess.Popen(_remote_debugging_cmd)
            _site = _site.strip()
            logging.info('Navigating to: ' + _site)
            s1 = urlparse(_site)
            _site_data_folder = os.path.join(_path, s1.netloc)
            if not os.path.isdir(_site_data_folder):
                os.mkdir(_site_data_folder)
                os.mkdir(os.path.join(_site_data_folder, 'dns'))
            _d_ip_dict = webDnsSetupMobile.setup_ip_subdomain(s1.netloc, archive_dir)
            webDnsSetupMobile.setup_nameserver(_d_ip_dict)
            webDnsSetupMobile.setup_webserver(s1.netloc, archive_dir, _d_ip_dict)
            print('Starting runs:')
            for run_no in range(10):
                _run_data_folder = os.path.join(_site_data_folder, 'run_' + str(run_no))
                if not os.path.isdir(_run_data_folder):
                    os.mkdir(_run_data_folder)
                    _subfolders = ['trace', 'screenshot', 'analysis', 'summary', 'tcpdump', 'perf']
                    for folder in _subfolders:
                        os.mkdir(os.path.join(_run_data_folder, folder))
                logging.info('Current profile: ' + net_profile['device_type'] + ' - ' + net_profile['name'] + ' run_no: ' + str(run_no) + ' site: ' + _site)
                #netns = network_emulator.NetworkEmulator(net_profile, dirs)
                #netns.set_profile(net_profile['conn_type'])
                os.system('pkill node')
                time.sleep(15)
                _trace_folder = os.path.join(_run_data_folder, 'trace')
                _screenshot_folder = os.path.join(_run_data_folder, 'screenshot')
                _summary_folder = os.path.join(_run_data_folder, 'summary')
                _trace_file = os.path.join(_trace_folder, str(run_no) + '_' + s1.netloc)
                _screenshot_file = os.path.join(_screenshot_folder, str(run_no) + '_' + s1.netloc)
                _summary_file = os.path.join(_summary_folder, str(run_no) + '_' + s1.netloc)
                logging.info(_trace_file, _screenshot_file, _summary_file)
                time.sleep(5)
                try:
                    _node_cmd = ['node', 'chrome_launcher.js', _site,  _trace_file, _summary_file, _screenshot_file]
                    subprocess.call(_node_cmd, timeout = 110)
                except subprocess.TimeoutExpired:
                    print("Timeout:  ", _site, run_no)
                    with open (os.path.join(_site_data_folder, 'log.txt'), 'w+') as _log:
                        _log.write("Timed out:  " +  _site + ' ' +  str(run_no) + '\n')
                time.sleep(15)
            pickle.dump(_d_ip_dict, open(os.path.join(_site_data_folder, 'dns/dnsBackup.txt'), 'wb'))
            time.sleep(2)
    stop = timeit.default_timer()
    logging.info(100*'-' + '\nTotal time: ' + str(stop -start)) 
if __name__ == '__main__':
    main()
