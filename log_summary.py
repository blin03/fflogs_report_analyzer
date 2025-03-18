from fflogsapi import FFLogsClient
from dotenv import load_dotenv
import os
import sys

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
# TODO: implement input and URL parser
# wow this difficulty field really is useless (unless??)
#log_url = '69ZDth1gyrKb4V32' # Extreme (difficulty=100)
log_url = 'jJnm6GwFxN3qPdD8' # Savage (difficulty=101)
#log_url = 'wxJvWMt18H4CcFgV' # Ultimate (difficulty=100)
report = client.get_report(log_url)


report_fightnames = {} # In format {fight: pulls(int)}
filtered_fights = [] # List of valid pulls

# Handle non-raid pulls and instant wipes (e.g. trash pulls noted at the bottom of each report)
for fight in report:
    duration = fight.end_time() - fight.start_time()
    if fight.difficulty() is None or duration < 15000: # wow the difficulty field is actually useful
        continue
    if fight.name() not in report_fightnames:
        report_fightnames.setdefault(fight.name(), 0)
    report_fightnames[fight.name()] += 1
    filtered_fights.append(fight)


kills = 0
wipes = 0
player_list = set()
pull_list = {} # In format {name: [kills(int), pulls(FFLogsFight obj)]}
player_stats = {} # In format {player_id: [name(str), deaths(int), DDs(int), pulls(int)]}


# TODO: Implement way to constrain game_zone to a single value based on user input
# TODO: Refactor to store values in variables, you dingus
print(f'Analysis of log at {log_url}:\n')
print(report_fightnames, '\n')
for fight in filtered_fights:
    # Append pull information to pull list
    pull_list.setdefault(fight.name(), [0])
    if not fight.is_kill():
        wipes += 1
        try:
            pull_list[fight.name()].append(f'Wipe {fight.percentage()}% ' + fight.last_phase(as_dataclass = True).name)
        except KeyError:
            pull_list[fight.name()].append(f'Wipe {fight.percentage()}%')
    else:
        kills += 1
        pull_list[fight.name()][0] += 1
        pull_list[fight.name()].append(fight.name() + " Kill " + str(pull_list[fight.name()][0]))


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
print(f'Kills: {kills}, ', f'Wipes: {wipes}', '\n')
for boss in pull_list:
    print(f'{boss}: ', ', '.join(pull_list[boss][1:]))
print('\n')
print('WHO GRIEFED? - Deaths are raw data, DDs are adjusted for mechanical wipes, and as such may not be fully accurate.')
for id in player_stats:
    print(f'{player_stats[id][0]}:', f'{player_stats[id][2]} damage downs,', player_stats[id][1], f'deaths in {player_stats[id][3]} pulls')


client.close()
client.save_cache()