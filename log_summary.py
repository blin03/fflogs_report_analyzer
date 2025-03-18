from fflogsapi import FFLogsClient
from dotenv import load_dotenv
import os

load_dotenv()

FFLOGS_CLIENT_ID = os.getenv('FFLOGS_CLIENT_ID')
FFLOGS_CLIENT_SECRET = os.getenv('FFLOGS_CLIENT_SECRET')

# Cringe workaround for FFLogs API's GQL query constructor force-converting string input, learn to write your own queries kids
class EnumWrapper:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

client = FFLogsClient(FFLOGS_CLIENT_ID, FFLOGS_CLIENT_SECRET)
client.clean_cache()
log_url = '14QbcmXg869qpAVW' # TODO: implement user input and url parser
#log_url = 'wxJvWMt18H4CcFgV'
report = client.get_report(log_url)


player_list = set()
pull_list = []
kills = 0
player_stats = {} # In format {player_id: [name, deaths, DDs, pulls]}

# TODO: Implement way to constrain game_zone to a single value based on user input
print(f'Analysis of log at {log_url}:\n')
for fight in report:
    # Handle non-raid pulls and instant wipes (e.g. trash pulls noted at the bottom of each report)
    duration = fight.end_time() - fight.start_time()
    if not fight.game_zone() or fight.game_zone() == "Unknown" or duration < 15000: # TODO: There has got to be a better way to do this man
        continue

    # Append pull information to pull list
    # TODO: Weird off-by-one discrepancy in pull count between players?
    if not fight.is_kill():
        pull_list.append(f'Wipe {fight.percentage()}% ' + fight.last_phase(as_dataclass = True).name)
    else:
        pull_list.append("Kill " + str(kills+1))
        kills += 1

    # Track and update player names and stats within player_stats
    player_details = fight.player_details()
    for player in player_details:
        player_list.add(player.name+"@"+player.server)
        if player.id not in player_stats:
            player_stats.setdefault(player.id, [player.name+"@"+player.server, 0, 0, 1])
        else:
            player_stats[player.id][3] += 1

    # Count up deaths
    deaths = fight.events(filters={'dataType': EnumWrapper('Deaths')})
    for death in deaths:
        player_stats[death['targetID']][1] += 1

    # Damage down aura ID: 1002911 (seems to be identical across zones?)
    dds = fight.table(filters = {'dataType': EnumWrapper('Debuffs'), 'abilityID': 1002911})
    for dd in dds['auras']:
        if dd['id'] not in player_stats: # Omit buff inheritances by pets
            continue
        if (fight.end_time() - dd['bands'][0]['startTime']) > 15000: # Omit cases where damage down is applied by a wipe condition (<15000ms prior to wipe)
            player_stats[dd['id']][2] += 1


print('Players: ', ', '.join(player_list), '\n')
print(f'Kills: {kills}, ', f'Wipes: {len(pull_list)-kills}', '\n')
print(', '.join(pull_list), '\n')
print('SUMMARY - deaths are raw data, DDs are adjusted for mechanical wipes, and as such may not be fully accurate.')
for id in player_stats:
    print(f'{player_stats[id][0]}:', f'{player_stats[id][2]} damage downs,', player_stats[id][1], f'deaths in {player_stats[id][3]} pulls')


client.close()
client.save_cache()