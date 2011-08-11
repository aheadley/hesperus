import opsview
import ..plugin
import time

class OpsviewPlugin(CommandPlugin,PollPlugin):
    MAX_STATE_DURATION = 12 * 60 * 60
    poll_interval = 15.0

    @plugin.Plugin.config_types(url=str, username=str, password=str, max_state_duration=int)
    def __init__(self, core, url=None, username=None, password=None, max_state_duration=43200):
        super(OpsviewPlugin, self).__init__(core)
        if any(map(lambda x: x is None, [url, username, password])):
            raise Exception('Missing setting')
        else:
            self.opsview_server = opsview.OpsviewServer(
                base_url=url,
                username=username,
                password=password)
            self.max_state_duration = max_state_duration
            self.alerting = []

    @plugin.CommandPlugin.register_command(r'status')
    def status_command(self, chans, name, match, direct, reply):
        reply('Alerts: ' + ', '.join(self.alerting))

    @plugin.CommandPlugin.register_command(r'ack\s+(\S+)(?:\s+(.*))')
    def ack_command(self, chans, name, match, direct, reply):
        pass

    @plugin.CommandPlugin.register_command(r'ackall\s+(.+)')
    def ackall_command(self, chans, name, match, direct, reply):
        self.opsview_server.remote.acknowledge_all(
            comment='%s via IRC: %s' % (name, match.group(1)))
        reply('Acknowledged all for %s' % name)

    def poll(self):
        alerting_now = []
        try:
            self.opsview_server.update([opsview.STATE_WARNING, opsview.STATE_CRITICAL])
        except opsview.OpsviewExcetpion, error:
            map(lambda chan: self.parent.send_outgoing(chan, error), self.channels)
        else:
            for host in self.opsview_server.children:
                if host['state'] == opsview.STATE_DOWN and \
                   host['current_check_attempt'] == host['max_check_attempts'] and \
                   host['state_duration'] < self.MAX_STATE_DURATION:
                    alerting_now.append('%s:%s' % host['name'], host['state'])
                else:
                    for service in host.children:
                        if service['current_check_attempt'] == service['max_check_attempts'] and \
                           service['state_duration'] < self.MAX_STATE_DURATION and \
                           'flapping' not in service:
                            alerting_now.append('%s[%s]:%s' % (host['name'], service['name'], service['state']))
            new_alerts = filter(lambda hash: hash not in self.alerting, alerting_now)
            recovered = filter(lambda hash: hash not in alerting_now, self.alerting)
            self.alerting = alerting_now
            recovered = 'Recovered: ' + ', '.join(recovered)
            if len(recovered) is not 0:
                map(lambda chan: self.parent.send_outgoing(chan,
                    'Recovered: ' + ', '.join(recovered)), self.channels)
            if len(new_alerts) is not 0:
                map(lambda chan: self.parent.send_outgoing(chan,
                    'New alerts: ' + ', '.join(new_alerts)), self.channels)
