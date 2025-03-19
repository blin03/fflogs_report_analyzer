from fflogsapi import FFLogsClient
from dotenv import load_dotenv
import os
import time

load_dotenv()
start = time.perf_counter()

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
# log_url = 'NdbQRaGLJf2VAkr8' # Dungeon (difficulty=10)
# log_url = '69ZDth1gyrKb4V32' # Extreme (difficulty=100)
# log_url = 'jJnm6GwFxN3qPdD8' # Savage (difficulty=101)
log_url = 'wxJvWMt18H4CcFgV' # Ultimate (difficulty=100)
report = client.get_report(log_url)


report_fightnames = {} # In format {fight: pulls(int)}
filtered_fights = [] # List of valid pulls

# Handle non-raid pulls and instant wipes (e.g. trash pulls noted at the bottom of each report)
for fight in report:
    fight_duration = fight.end_time() - fight.start_time()
    fight_difficulty = fight.difficulty()
    
    if fight_difficulty is None or fight_duration < 15000: # wow the difficulty field is actually useful
        continue

    fight_name = fight.name()
    if fight_name not in report_fightnames:
        report_fightnames.setdefault(fight_name, 0)
    report_fightnames[fight_name] += 1
    filtered_fights.append(fight)

kills = 0
wipes = 0
player_list = set()
pull_list = {} # In format {name: [kills(int), pulls(FFLogsFight obj)]}
player_stats = {} # In format {player_id: [name(str), deaths(int), DDs(int), pulls(int)]} 

# TODO: Implement way to constrain game_zone to a single value based on user input
print(f'Analysis of log at {log_url}:\n')
print(report_fightnames, '\n')
for fight in filtered_fights:
    fight_name = fight.name()
    fight_kill = fight.is_kill()
    fight_percentage = fight.percentage()
    fight_end = fight.end_time()
    pull_list.setdefault(fight_name, [0])

    # TODO: Make this run faster somehow
    start2 = time.perf_counter()
    try:
        last_phase = fight.last_phase(as_dataclass=True).name
    except KeyError:
        last_phase = None
    end2 = time.perf_counter()
    # print(f'time to fetch last phase of {fight_name}: {end2-start2}s')
    

    # Populate pull_list with kill/wipe percentage for current fight
    if not fight_kill:
        wipes += 1
        pull_list[fight_name].append(f'Wipe {fight_percentage}% ' + (last_phase if last_phase else ''))
    else:
        kills += 1
        pull_list[fight_name][0] += 1
        pull_list[fight_name].append(fight_name + " Kill " + str(pull_list[fight_name][0]))
    
    # Track player ids, names, and pull counts in player_stats
    player_details = fight.player_details()
    for player in player_details:
        player_key = f"{player.name}@{player.server}"
        player_id = player.id
        player_list.add(player_key)
        if player_id not in player_stats:
            player_stats[player_id] = [player_key, 0, 0, 1]
        else:
            player_stats[player_id][3] += 1
    
    # Track player death counts in player_stats
    deaths = fight.events(filters={'dataType': EnumWrapper('Deaths')})
    for death in deaths:
        player_stats[death['targetID']][1] += 1
    
    # Track damage down aura applications in player_stats
    # Damage down aura ID: 1002911 (seems to be identical across zones?)
    dds = fight.table(filters={'dataType': EnumWrapper('Debuffs'), 'abilityID': 1002911})
    for dd in dds['auras']:
        if dd['id'] not in player_stats:
            continue
        if (fight_end - dd['bands'][0]['startTime']) > 15000:
            player_stats[dd['id']][2] += 1

print('Players: ', ', '.join(player_list), '\n')
print(f'Kills: {kills}, ', f'Wipes: {wipes}', '\n')
for boss in pull_list:
    print(f'{boss}: ', ', '.join(pull_list[boss][1:]))
print('\n')
print('WHO GRIEFED? - Deaths are raw data, DDs are adjusted for mechanical wipes, and as such may not be fully accurate.')
for id in player_stats:
    print(f'{player_stats[id][0]}:', f'{player_stats[id][2]} damage downs,', player_stats[id][1], f'deaths in {player_stats[id][3]} pulls')

end = time.perf_counter()
print(f'ran in {end - start:.4f}s')
client.close()
client.save_cache()
