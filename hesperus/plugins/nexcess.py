import re
import socket
import random
import urllib
from time import time

from ..plugin import PassivePlugin, PollPlugin
from ..core import ET
from ..shorturl import short_url
import nocworx

class NocworxPlugin(PollPlugin, PassivePlugin):
    URL_SEARCH = '{hosturl}search?q={query}'
    URL_ALLOCATION = '{hosturl}allocation-dedicated/overview?allocation_id={allocation_id}'
    REPLY_SERVER_LOOKUP = '{ip} ({service_desc}) should have {cpu_used}x{cpu_desc}, {ram_desc} ' \
        'RAM, and {drives} <{short_url}>'
    REPLY_SERVER_LOCATION = '{host} ({alloc[main_ip]}) is at {alloc[location]} / ' \
        '{alloc[network-switches][0][hostname]}#{alloc[network-switches][0][ports][0][name]} / ' \
        '{alloc[power-switches][0][hostname]}#{alloc[power-switches][0][ports][0][name]} <{short_url}>'
    REPLY_SERVICE_INFO = '(btw: {ip} is a ({status}) {desc} with {ip_count} IPs <{short_url}>)'

    poll_interval = 1500.0

    @PassivePlugin.config_types(hosturl=str, username=str, password=str, no_match_urls=ET.Element, chance=float, cooldown=int)
    def __init__(self, core, hosturl, username, password, no_match_urls=None, chance=0.10, cooldown=120):
        super(NocworxPlugin, self).__init__(core)
        self._hosturl = hosturl
        self._api = nocworx.NocworxApi(self._hosturl, username, password)
        self._chance = chance
        if no_match_urls:
            self._no_match_urls = [el.text.strip() for el in no_match_urls \
                if el.tag.lower() == 'url']
        else:
            self._no_match_urls = []
        self._recent_ips = {}
        self._cooldown = cooldown

    @PassivePlugin.register_command(r'(?:noc)?loc\s+(.+)')
    def look_up_location(self, chans, name, match, direct, reply):
        host = match.group(1).strip()
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror:
            reply('I dunno what that is')
            return
        try:
            allocs = self._api.allocation_dedicated.list(search=ip)
            for alloc in allocs:
                self.log_debug(alloc)
                if ip in alloc['ip_addresses']:
                    reply(self.REPLY_SERVER_LOCATION.format(host=match.group(1),
                        alloc=alloc, short_url=short_url(self.URL_ALLOCATION.format(
                            hosturl=self._hosturl, allocation_id=alloc['allocation_id']))))
                    return
            else:
                self._no_matches_reply(reply, host)
        except nocworx.ApiException as e:
            reply('API Error: {0}: {1}'.format(e.__class__.__name__, e))

    @PassivePlugin.register_command(r'nocsrv\s+(.+)')
    def look_up_server(self, chans, name, match, direct, reply):
        host = match.group(1).strip()
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror:
            reply('I dunno what that is')
            return
        try:
            services = self._api.client_service.list(search=ip)
            for service in services:
                allocations = self._api.client_service_hosting.list_allocations(
                    service_id=service['service_id'])
                for allocation in allocations:
                    servers = self._api.allocation_dedicated.list_servers(
                        allocation_id=allocation['allocation_id'])
                    for server in servers:
                        s = self._api.server.list(search='id:{server_id}'.format(**server))
                        if s:
                            reply(self.REPLY_SERVER_LOOKUP.format(
                                ip=host, service_desc=service['description'],
                                drives=self._get_drive_count(s[0]),
                                short_url=short_url(self.URL_ALLOCATION.format(
                                    hosturl=self._hosturl,
                                    allocation_id=allocation['allocation_id'])),
                                **s[0]))
                            return
            else:
                self._no_matches_reply(reply, host)
                        return
        except nocworx.ApiException as e:
            reply('API Error: {0}: {1}'.format(e.__class__.__name__, e))

    @PassivePlugin.register_pattern(r'((?:\d{1,3}\.){3}\d{1,3})')
    def service_info(self, chans, name, match, direct, reply):
        if direct: return
        ip = match.group(1).strip()
        now = int(time())
        if not self._ip_on_cooldown(ip) and \
                not any(ip.startswith(subnet) for subnet in ['127.', '10.', '192.168.', '172.']):
            try:
                self._recent_ips[ip] = now
                services = self._api.client_service.list(search=ip)
                for service in services:
                    allocations = self._api.client_service_hosting.list_allocations(
                        service_id=service['service_id'])
                    for allocation in allocations:
                        allocation_infos = self._api.allocation_dedicated.list(
                            search='id:' + str(allocation['allocation_id']))
                        for allocation_info in allocation_infos:
                            if ip in allocation_info['ip_addresses']:
                                reply(self.REPLY_SERVICE_INFO.format(
                                    ip=ip,
                                    status=service['status'],
                                    desc=service['description'],
                                    ip_count=len(allocation_info['ip_addresses']),
                                    short_url=short_url(self.URL_ALLOCATION.format(
                                        hosturl=self._hosturl,
                                        allocation_id=allocation['allocation_id']))
                                    ))
                                return
            except nocworx.ApiException as e:
                self.log_warning(e)

    def poll(self):
        self.log_debug('Sending NocWorx session keep-alive...')
        self._api.api.set(**{'max-results': 10})
        yield

    def _ip_on_cooldown(self, ip):
        return not (ip not in self._recent_ips or \
            (ip in self._recent_ips and int(time()) - self._recent_ips[ip] > self._cooldown))

    def _get_drive_count(self, server):
        types = list(set(v for (k, v) in server.iteritems() \
            if k.startswith('hdd') and k.endswith('_desc') and not v.startswith('0')))
        drive_count = dict((k, len([v for v in server.itervalues() if v == k])) \
            for k in types)
        return ', '.join('{c}x{d}'.format(c=c, d=d) for (d, c) in drive_count.iteritems())

    def _no_matches_reply(self, reply, query=None):
        if self._no_match_urls and random.random() < self._chance:
            reply('No matches, maybe you\'d be interested in this though: <{0}>'.format(
                short_url(random.choice(self._no_match_urls))))
        else:
            if query:
                reply('No matches found, try the search results: <{0}>'.format(
                    short_url(self.URL_SEARCH.format(hosturl=self._hosturl,
                        query=urllib.quote_plus(query)))))
            else:
                reply('No matches found, sorry :C')
