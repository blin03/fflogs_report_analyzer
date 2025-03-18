from fflogsapi import FFLogsClient
from dotenv import load_dotenv
import os

load_dotenv()

FFLOGS_CLIENT_ID = os.getenv('FFLOGS_CLIENT_ID')
FFLOGS_CLIENT_SECRET = os.getenv('FFLOGS_CLIENT_SECRET')


client = FFLogsClient(FFLOGS_CLIENT_ID, FFLOGS_CLIENT_SECRET)
client.clean_cache()
log_url = 'ZaqprDxc8v3FPgLV' # TODO: implement user input
#log_url = 'wxJvWMt18H4CcFgV'
report = client.get_report(log_url)

#TODO: find a master zone list, make csv, import into main
for fight in report:
    print(fight.game_zone())
    print(fight.name())

client.close()
client.save_cache()