import errno
import random
import sys
import subprocess
import os
import shutil
from urllib.parse import urlparse
import time
from OpenSSL import crypto, SSL
from socket import gethostname
from pprint import pprint
from time import gmtime, mktime
import tldextract


def create_self_signed_cert(cert_dir, key_dir, domain_name):
    SYSTEM_CERT_DIR = '/usr/local/share/ca-certificates'
    DOMAIN_SYS_DIR = os.path.join(SYSTEM_CERT_DIR, domain_name)
    CERT_FILE = domain_name + '.crt'
    KEY_FILE = domain_name + '.key'
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 1024)
    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().ST = "New York"
    cert.get_subject().L = "Stony Brook"
    cert.get_subject().O = "Computer Science"
    cert.get_subject().OU = "NetSys"
    cert.get_subject().CN = domain_name
    cert.set_serial_number(int(random.randint(0, 1000000000)))
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha1')
    #print(cert_dir, CERT_FILE, crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    open(os.path.join(cert_dir, CERT_FILE), "wb").write(
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    open(os.path.join(key_dir, KEY_FILE), "wb").write(
        crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    clear_folder(DOMAIN_SYS_DIR)
    system_cert_domain = os.path.join(DOMAIN_SYS_DIR, CERT_FILE)
    shutil.copy2(os.path.join(cert_dir, CERT_FILE), system_cert_domain)
    #print(' '.join(['certutil', '-d', 'sql:/home/jnejati/.pki/nssdb','-A','-t', '"C,,"', '-n', domain_name, '-i', system_cert_domain]))
    #subprocess.call(['certutil', '-d', 'sql:/home/jnejati/.pki/nssdb','-D','-t', '"C,,"', '-n', domain_name, '-i', system_cert_domain])
    #subprocess.call(['certutil', '-d', 'sql:/home/jnejati/.pki/nssdb','-A','-t', '"C,,"', '-n', domain_name, '-i', system_cert_domain])
    os.system('certutil -d sql:/home/jnejati/.pki/nssdb -D -t "C,," -n ' + domain_name +  ' -i ' + system_cert_domain)
    os.system('certutil -d sql:/home/jnejati/.pki/nssdb -A -t "C,," -n ' + domain_name +  ' -i ' + system_cert_domain)

def clear_folder(folder):
    if os.path.isdir(folder):
            for root, dirs, l_files in os.walk(folder):
                for f in l_files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
    else:
        os.makedirs(folder)

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def copyanything(src, dst):
    try:
        copytree(src, dst)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else: raise


def setup_webserver(domain, archive_dir, _d_ip_dict):
    print('domain ', domain)
    os.system('pkill nginx')
    time.sleep(1)
    _cert_dir = '/home/jnejati/PLTSpeed/confs/certs'
    _key_dir = '/home/jnejati/PLTSpeed/confs/keys'
    _dest = '/var/www/'
    _src = os.path.join(archive_dir, domain)
    clear_folder(_dest)
    clear_folder(_cert_dir)
    clear_folder(_key_dir)
    copyanything(_src, _dest)
    nginx_file_path = '/etc/nginx/nginx.conf'
    nginx_f = open(nginx_file_path, 'w')
    out = """user  nginx;
            worker_processes  1;
            worker_rlimit_nofile 30000;
            error_log  /var/log/nginx/error.log warn;
            pid        /var/run/nginx-new.pid;
            events {
                worker_connections  1024;
                 } 
            http {
                server_names_hash_bucket_size  4096;
                include       /etc/nginx/mime.types;
                default_type  application/octet-stream;
                log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                                  '$status $body_bytes_sent "$http_referer" '
                                  '"$http_user_agent" "$http_x_forwarded_for"';
                sendfile        on;
                keepalive_timeout  65;\n"""
    for _domain, sd_ip in _d_ip_dict.items():
        for _subdomain_ip in sd_ip:
            for _subdomain, _ip in _subdomain_ip.items():
                if _subdomain == '@':
                    _site = _domain
                else:
                    _site = _subdomain + '.' + _domain
                create_self_signed_cert(_cert_dir, _key_dir, _site)
                out = out + """server {
                    listen              %s:80;
                    listen 	            %s:443 ssl;
                    server_name         %s;
                access_log  /var/log/nginx/%s.access.log  main;
                ssl_certificate     /home/jnejati/PLTSpeed/confs/certs/%s.crt;
                ssl_certificate_key /home/jnejati/PLTSpeed/confs/keys/%s.key;
                location / {
                    root   /var/www/%s;
                    index  index.html index.htm, index.php;
                 }
            index  index.html index.htm;
         }\n""" % (_ip, _ip, _site, _site, _site, _site, _site)
    out = out + '}\n'
    #print(out)
    nginx_f.write(out)
    nginx_f.close()
    #subprocess.call(['dpkg-reconfigure', 'ca-certificates'])
    subprocess.call(['/usr/sbin/nginx', '-c', '/etc/nginx/nginx.conf'])

def setup_ip_subdomain(domain, archive_dir):
    _domains = os.listdir(os.path.join(archive_dir, domain))
    _d_ip_dict = {}
    for i in range(len(_domains)):
        _set_ip_alias = ['ifconfig', 'enp1s0f0:' +  str(10 + i), '192.168.1.' + str(10 + i), 'up']
        subprocess.call(_set_ip_alias)
    _interface_id = 10
    for _d in _domains:
        if not _d == 'trace' and not _d =='screenshot':
            _ext = tldextract.extract(_d)
            _subdomain = _ext.subdomain
            _domain = _ext.domain
            _suffix = _ext.suffix
            _interface_id += 1
            _ip = '192.168.1.' + str(_interface_id)
            if not _subdomain == '':
                _d_ip_dict.setdefault(_domain + '.' +  _suffix, []).append({_subdomain:_ip})
            else:
                _d_ip_dict.setdefault(_domain + '.' +  _suffix, []).append({'@':_ip})
    return _d_ip_dict
                
def setup_nameserver(_d_ip_dict):
    bind_file_path = '/etc/bind/named.conf.local'
    bind_f = open(bind_file_path, 'w')
    bind_f_text = ""
    for _domain, sd_ip in _d_ip_dict.items():
       bind_f_text = bind_f_text + """zone "%s" IN {
    type master;
    file "/var/lib/bind/db.%s";
};\n"""  %  (_domain, _domain)
       out = """$TTL 3H
@   IN SOA  @ hostmaster.%s. (
                0   ; serial
                3H  ; refresh
                1H  ; retry
                1W  ; expire
                3H )    ; minimum
@            IN   NS     ns1.%s.
ns1          IN   A      192.168.1.2
"""    % (_domain, _domain)
       for _subdomain_ip in sd_ip:
           for _subdomain, _ip in _subdomain_ip.items():
               #print(_subdomain, _domain, _ip)
               out = out + '%s      IN      A       %s\n' % (_subdomain, _ip)
       #print(out)
       target = open('/var/lib/bind/db.%s' % _domain, 'w')
       target.write(out)
       target.close()
    bind_f.write(bind_f_text)
    bind_f.close()
    subprocess.call(['/etc/init.d/bind9', 'restart'])


#setup_ip_subdomain('stackoverflow.com', '/home/jnejati/PLTSpeed/record/archive')
