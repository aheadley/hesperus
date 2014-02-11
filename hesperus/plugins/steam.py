from hesperus.plugin import CommandPlugin, PersistentPlugin, PollPlugin
import steamapi

class SteamPlugin(PollPlugin, PersistentPlugin, CommandPlugin):
    PLUGIN_DATA_VERSION     = 1000
    STEAM_ID_MAGIC_NUMBER   = 0x110000100000000 # 76561197960265728
    poll_interval           = 30
    persistence_file        = 'steam.json'

    @CommandPlugin.config_types(steam_api_key=str)
    def __init__(self, core, steam_api_key):
        super(SteamPlugin, self).__init__(core)

        self._steam_conn = steamapi.core.APIConnection(api_key=steam_api_key)
        self._update_data()

    def poll(self):
        yield

    @CommandPlugin.register_command(r'watchgame\s+(\d+)')
    def add_game_to_track(self, chans, name, match, direct, reply):
        if match.group(1):
            app_id = int(match.group(1))
            app = steamapi.app.SteamApp(app_id)
            if app.id in self._data['apps']:
                del self._data['apps'][app.id]
                reply('Removed game [%d:%s] from my watch list' % (app.id, app.name))
            else:
                self._data['apps'][app.id] = app.name
                reply('Added game [%d:%s] to my watch list' % (app.id, app.name))

    @CommandPlugin.register_command(r'watchplayer\s+(.+)')
    def add_player_to_track(self, chans, name, match, direct, reply):
        if match.group(1):
            player_id = match.group(1)
            if player_id.isdigit() and len(player_id) >= 17:
                player_id = int(player_id)
            elif player_id.upper().startswith('STEAM_0:'):
                player_id = self._steam_id_to_friend_id(player_id)
            else:
                reply('Unrecogonized steam ID format')
                return
            player = self._get_steam_user(player_id)
            if player.id in self._data['users']:
                reply('Removed user [%d:%s] from my watch list' % (player.id, player.name))
            else:
                self._data['users'][player.id] = {
                    'irc_nick': name,
                }
                reply('Added user [%d:%s] to my watch list' % (player.id, player.name))

    @CommandPlugin.register_command(r'steamstatus')
    def steam_status(self, chans, name, match, direct, reply):
        pass

    @CommandPlugin.register_command(r'announce\s+(.+)')
    def announce_game(self, chans, name, match, direct, reply):
        pass

    def _update_data(self):
        if self._data.get('version', 0) == 0:
            self._data['users'] = {}
            self._data['apps'] = {}
            self._data['status'] = {}
            self._data['version'] = self.PLUGIN_DATA_VERSION

    def _get_steam_user(self, friend_id):
        return steamapi.user.SteamUser(friend_id)

    def _steam_id_to_friend_id(self, steam_id):
        # @source http://forums.alliedmods.net/showpost.php?p=531769&postcount=1
        toks = steam_id.split(':')
        server_id = int(toks[1])
        auth_id = int(toks[2])
        return auth_id * 2 + self.STEAM_ID_MAGIC_NUMBER + server_id


    def _friend_id_to_steam_id(self, friend_id):
        server_id = friend_id % 2
        auth_id = (friend_id - self.STEAM_ID_MAGIC_NUMBER - server_id) / 2
        return 'STEAM_0:%d:%d' % (server_id, auth_id)
