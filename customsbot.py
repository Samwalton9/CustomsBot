import discord
import asyncio
import datetime
import random
import os

# TODO: When someone receives the custom role, PM them information.

client = discord.Client()

"""Checks if the logs folder exists, creates it if it isn't."""
folder_exists = os.path.isdir("logs")
if not folder_exists:
        os.mkdir("logs")

def get_custom_games():
    """Returns a dict containing #custom-games and #custom-hosters objects"""
    customs_hosters = client.get_channel('375276183777968130')
    customs_channel = client.get_channel('317770788524523531')

    if debug:
        customs_hosters = client.get_channel('382550498533703680')  # bot-testing in my server
        customs_channel = customs_hosters  # Test in the same channel.

    channels = {'hosters': customs_hosters, 'games': customs_channel}

    return channels

def log_command(message_object, text):
    """Whenever a command is sent, log it to the logfile"""
    current_folder = os.path.dirname(__file__)
    file_path = os.path.join(current_folder, 'logs')
    logfile = os.path.join(file_path, datetime.datetime.now().strftime("%Y%m%d") + ".txt")
    with open(logfile,"a") as file:
        log_string = (str(message_object.timestamp) + " | " + text + " | " + message_object.author.name + "#" + message_object.author.discriminator + "\n")
        file.write(log_string)

def most_reactions(message):
    """
    Given a message, determine which reaction emoji received the
    most votes. Breaks ties with a random choice.
    """
    reaction_emojis, reaction_count = [], []
    for message_reaction in message.reactions:
        reaction_emojis.append(message_reaction.emoji)
        reaction_count.append(message_reaction.count)

    max_emoji = [reaction_emojis[i] for i,x in enumerate(reaction_count) if x == max(reaction_count)]
    num_emojis = len(max_emoji)

    if num_emojis == 1:
        return max_emoji[0]
    else:
        i = random.randint(0,num_emojis-1)
        return max_emoji[i]

def get_countdown_string(timedelta_object):
    """Given a timedelta object, returns a mm:ss time string"""
    countdown_timer_split = str(timedelta_object).split(":")
    countdown_timer_string = ":".join(countdown_timer_split[1:])
    return countdown_timer_string.split(".")[0]  # Without decimal

@client.event
async def on_ready():
    await client.change_presence(game=discord.Game(name="DM for info"))

    print('Logged in as', client.user.name)
    print('\nLogged in to the following servers:')
    for server in client.servers:
        print(server.name)
    print('-----')

@client.event
async def on_message(message):
    """Check every message for a command, trust any from #custom-hosters"""
    is_command = message.content.startswith('$')

    if is_command:
        customs_channel = get_custom_games()
        if message.channel == customs_channel['hosters']:
            await parse_command(message)

    is_pm = message.channel.is_private

    if is_pm and "CustomsBot" not in message.author.name:
        pm_response = ("Hi! We run custom games multiple times every week,"
                       " and I would be happy to give you more information."
                       "\n\nIf you don't yet have the 'Custom' role, which "
                       "allows you to see #custom-games and "
                       "#custom-chat-lfg, please respond with `role` and"
                       " I'll add it to your account.\n\n"
                       "If you would like a link to the schedule, please "
                       "respond with `schedule`.\n\n"
                       "To receive a link to the Twitch stream, please "
                       "reply `twitch`.\n\n"
                       "If you want to sign up as a hoster or suggest a "
                       "new game mode, please reply `forms`."
                      )

        num_pms = 0
        async for pm_message in client.logs_from(message.channel, limit=20):
            num_pms += 1

        if num_pms > 1:
            await parse_pm(message)
        else:
            print("Sent instructions to", message.author.name)
            await client.send_message(message.channel, content=pm_response)        

async def parse_command(message_object):
    """
    After a command has been identified, get the primary command and run
    the relevant function.
    """
    command_string = message_object.content

    split_command = command_string[1:].split(" ")
    primary_command = split_command[0].lower()
    options = split_command[1:]

    current_folder = os.path.dirname(__file__)
    file_path = os.path.join(current_folder, 'logs')
    logfile = os.path.join(file_path, datetime.datetime.now().strftime("%Y%m%d") + ".txt")

    if primary_command in command_list:
        result = await command_list[primary_command](message_object)
    else:
        with open(logfile,"a") as file:
            file.write(str(message_object.timestamp) + " | INCORRECT COMMAND | " + primary_command + " | " + message_object.author.name + "#" + message_object.author.discriminator + "\n")
        result = "Error: That command doesn't exist. To see a list of available commands type $help."

    if result:
        await client.send_message(message_object.channel, content=result)

async def parse_pm(message_object):
    pm_commands = ['role', 'schedule', 'twitch', 'forms']
    pm_channel = message_object.channel
    sent_command = message_object.content.lower()
    full_username = message_object.author.name + "#" + message_object.author.discriminator
    
    current_folder = os.path.dirname(__file__)
    file_path = os.path.join(current_folder, 'logs')
    logfile = os.path.join(file_path, datetime.datetime.now().strftime("%Y%m%d") + ".txt")

    if sent_command in pm_commands:
        if sent_command == 'role':
            pubg_server = client.get_server("289466476187090944")
            pubg_member = pubg_server.get_member(message_object.author.id)
            member_roles = pubg_member.roles
            custom_role_id = "318030585647857665"

            has_role = False
            for role in member_roles:
                if role.id == custom_role_id:
                    has_role = True
                    break

        if not debug:
            if has_role:
                pm_text = ("You already have the 'Custom' role and should be able to see "
                           "#custom-games and #custom-chat-lfg already.")
            else:
                custom_role = discord.utils.get(pubg_server.roles, id=custom_role_id)
                await client.add_roles(pubg_member, custom_role)
                print("Gave Custom role to", full_username)
                pm_text = ("Added the Custom role successfully. You should now be able to "
                           "see #custom-games and #custom-chat-lfg.")
        else: 
            print("Role assignment is not available in debug mode.")
            pm_text = None


        if sent_command == 'schedule':
            pm_text = ("A full schedule of upcoming games can be found at <https://goo.gl/TQ8GoH>"
                       "\n\nThe schedule should be shown in your time zone, but you can verify "
                       "this by checking the menu in the top right."
                       "\n\n*If the schedule appears to be blank, we may not have any games "
                       "currently planned. Check back soon to see if we've added any!*")
        if sent_command == 'twitch':
            pm_text = ("All our games are streamed over at our Twitch channel: "
                       "<https://twitch.tv/pubgreddit>\n\n"
                       "Twitch subscribers get access to #super-secret-sub-club, "
                       "where passwords for custom games are posted before being "
                       "announced publicly. Any funds raised through subscriptions "
                       "will go into future tournaments! Once you've subscribed "
                       "just make sure your Twitch account is linked to your "
                       "Discord account and you should get the role!")
        if sent_command == 'forms':
            pm_text = ("The game modes we play are usually taken from this list, "
                       "which we continue to expand with new modes: "
                       "<https://goo.gl/JU1ds1> You can suggest new modes using "
                       "this form: <https://goo.gl/forms/b8AZGpSQpvkj1suj1>\n\n"
                       "If you have experience streaming games on Twitch "
                       "(with a solid internet connection and a PC good enough "
                       "to handle it), and have the availability to host at "
                       "least approximately once per week, please let us know "
                       "by filling out this form: <https://goo.gl/forms/H1QrCeS2KZ1JB8IE3>")

        
        with open(logfile,"a") as file:
            file.write(str(message_object.timestamp) + " | Successfully parsed command from " + full_username + " | " + sent_command + "\n")
        
        if pm_text:
            await client.send_message(pm_channel, content=pm_text)
    else:
        with open(logfile,"a") as file:
            file.write(str(message_object.timestamp) + " | Failed to parse command from " + full_username + " | " + sent_command + "\n")
        error_message = "Sorry, I don't recognise that command."
        await client.send_message(pm_channel, content=error_message)

async def squad_vote(command_message):
    """
    Starts a vote on squad size.

    The hoster can specify squad sizes to be used, or 'all' to include
    every size between 1 and 10. If there are no arguments, the vote
    defaults to 1, 2, 4, and 8. The vote stays open for 2 minutes.

    Once a winner is determined, set_voice_limit() is run for the
    winning size.
    """
    command_sent = command_message.content
    message_squad_sizes = command_sent.split(" ")[1:]
    
    if len(message_squad_sizes) == 0:
        default_squad_sizes = [1, 2, 4, 8]
        squad_sizes_selected = default_squad_sizes
    else:
        if message_squad_sizes[0] == "all":
            squad_sizes_selected = range(1,11)
        else:
            try:
                sizes_selected = [int(i) for i in message_squad_sizes]
                squad_sizes_selected = sorted(sizes_selected)
            except ValueError:
                return "Error: Please only use integers as arguments for `squadvote`."

            squads_correct_range = all(i >= 1 and i <= 10 for i in squad_sizes_selected)
            if not squads_correct_range:
                return "Error: Please only use integers between 1 and 10 for `squadvote`."            

    customs_channel = get_custom_games()

    squad_vote_message = "Please vote on squad size for the next game:\nTimer: {}"
    default_message = squad_vote_message.format("02:00")
    
    sent_squad_message = await client.send_message(customs_channel['games'], content= default_message)

    for squad_size_int in squad_sizes_selected:
        if squad_size_int == 10:
            emoji = "\U0001F51F"  # :keycap_ten: is a single emoji
        else:
            emoji = str(squad_size_int) + "\U000020e3"

        await client.add_reaction(sent_squad_message, emoji)

    here_ping = await client.send_message(customs_channel['games'], content="@here")

    message_channel = command_message.channel
    await client.send_message(message_channel, "Squad size vote successfully posted.")
    log_command(command_message, "Squad vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = squad_vote_message.format(countdown_timer_string)
        await client.edit_message(sent_squad_message, new_message)

    sent_squad_message = await client.get_message(customs_channel['games'], sent_squad_message.id)
    await client.clear_reactions(sent_squad_message)

    squad_selected = most_reactions(sent_squad_message)

    squad_result = squad_selected + "P Squads"

    squad_message_finished = "Squad size vote over. Result: {}".format(squad_result)
    await client.edit_message(sent_squad_message, squad_message_finished)

    await client.delete_message(here_ping)

    await set_voice_limit(user_limit=squad_selected)

async def region_vote(command_message):
    """
    Starts a vote on region to host on.

    Hoster has no control over this one; it just adds every region's emoji
    and determines the winner.
    """
    region_emoji_ids = [
               '333366981959090186',  # Asia
               '333366950455672833',  # EU
               '379707501282590720',  # KJP
               '333366997729411082',  # NA
               '333366933657223168',  # OCE
               '333366961792876544',  # SA
               '333366971586445313',  # SEA
               ]

    customs_channel = get_custom_games()

    region_vote_message = "Which region should we host today's games on?\nTimer: {}"
    default_region_message = region_vote_message.format("02:00")
    sent_region_message = await client.send_message(customs_channel['games'], content= default_region_message)

    for region_emoji in region_emoji_ids:
        region_emoji_obj = discord.utils.get(client.get_all_emojis(), id=region_emoji)
        await client.add_reaction(sent_region_message, region_emoji_obj)

    here_ping = await client.send_message(customs_channel['games'], content="@here")

    message_channel = command_message.channel
    await client.send_message(message_channel, "Region vote successfully posted.")
    log_command(command_message, "Region vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = region_vote_message.format(countdown_timer_string)
        await client.edit_message(sent_region_message, new_message)

    sent_region_message = await client.get_message(customs_channel['games'], sent_region_message.id)
    await client.clear_reactions(sent_region_message)
    region_selected = most_reactions(sent_region_message)

    region_result = region_selected

    region_message_finished = "Region vote over. Result: {}".format(region_result)

    await client.delete_message(here_ping)

    await client.edit_message(sent_region_message, region_message_finished)

async def password_countdown(command_message):
    """
    Starts a countdown to password release in #custom-games. Immediately
    posts server name and password to #mods and #super-secret-sub-club,
    pinging @here in SSSC only.

    Hoster must specify a password, and may optionally specify the number
    of minutes until the password is released. Defaults to 5 minutes.
    """
    split_message = command_message.content.split(" ")
    message_length = len(split_message)
    if message_length not in [2, 3]:
        return "Incorrect number of arguments given."

    password = split_message[1]
    if message_length == 3:
        timer = split_message[2]
        try:
            num_seconds = int(split_message[2])*60
        except ValueError:
            return "Error: Please use an integer to denote the countdown length for `password`."
    else:
        num_seconds = 300
    customs_channel = get_custom_games()

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=num_seconds)
    countdown_timer = time_to_post - datetime.datetime.now()
    countdown_timer_string = get_countdown_string(countdown_timer)

    template_string = "Server name: PUBG Reddit\nPassword: {}"

    default_text = template_string.format("[" + countdown_timer_string + "]")
    result_string = template_string.format(password)

    countdown_message = await client.send_message(customs_channel['games'], default_text)

    mods_channel = client.get_channel('340575221495103498')
    sssc_channel = client.get_channel('340984090109018113')
    
    if not debug:
        for channel_name in [mods_channel, sssc_channel]:
            await client.send_message(channel_name, result_string)
            if channel_name == sssc_channel:
                await client.send_message(channel_name, content="@here")

    log_command(command_message, "Password")

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = template_string.format("[" + countdown_timer_string + "]")
        await client.edit_message(countdown_message, new_message)

    await client.edit_message(countdown_message, result_string)
    await client.send_message(customs_channel['games'], content="@here")

async def set_voice_limit(command_message=None, user_limit=None):
    """
    Changes all custom games voice channel sizes to the one specified.

    Can be run either directly via $setvoicelimit or indirectly in
    other functions.
    """
    if command_message:
        split_message = command_message.content.split(" ")
        message_length = len(split_message)
        if message_length == 2:
            voice_limit = split_message[1]
            try:
                voice_limit_int = int(voice_limit)
            except ValueError:
                return "Error: Please use an integer to denote the size of voice channels."    
        else:
            return "Error: Wrong number of arguments given."
    if user_limit:
        if len(user_limit) > 1:
            voice_limit_int = int(user_limit[:-1])  # Unicode to int
        else:
            voice_limit_int = 10

    customs_channel = get_custom_games()

    all_channels = client.get_all_channels()
    for channel in all_channels:
        if channel.name.startswith("\U0001F6E0"):
            await client.edit_channel(channel, user_limit=voice_limit_int)

    voice_limit_message = "Set custom games voice channels to new user limit of {}.".format(voice_limit_int)

    await client.send_message(customs_channel['hosters'], voice_limit_message)

async def remove_messages(command_message):
    """
    Removes a number of CustomsBot messages from #custom-games.

    Hosters aren't necessarily mods, so they need some way to clear
    CustomsBot's messages. This function removes either a set amount
    or all of CustomsBot's messages.
    """
    message_split = command_message.content.split(" ")
    message_length = len(message_split)
    num_messages = message_split[1]

    if message_length != 2:
        return "Incorrect number of arguments given."
    if num_messages != 'all':
        try:
            num_messages = int(num_messages)
        except ValueError:
            return "Error: Please use an integer to denote the number of messages to clear."
    
    customs_channel = get_custom_games()

    message_count = 0
    messages_to_remove = []

    # Defaults to only retrieving 100 messages from #custom-games.
    # Has the potential to cause an issue, but should rarely ever do so.
    async for message in client.logs_from(customs_channel['games']):
        if message.author.id == '399360578956689409':
            if num_messages == 'all':
                messages_to_remove.append(message)
            else:
                messages_to_remove.append(message)
                message_count += 1
                if message_count == num_messages:
                    break

    for customsbot_message in messages_to_remove:
        await client.delete_message(customsbot_message)

    confirmation_text = "Removed {} CustomsBot messages from #custom-games.".format(num_messages)
    await client.send_message(command_message.channel, confirmation_text)

    log_command(command_message, "Remove messages ({})".format(num_messages))

async def help_list(command_message):
    """Prints an embedded list of commands."""
    command_channel = command_message.channel
    list_of_commands = '''
    `squadvote <squad size 1> <squad size 2> ...` - Post a vote for squad size for the next game, defaults to 1, 2, 4, and 8. `squadvote all` will do every size between 1 and 10. Automatically changes voice channel sizes to winning vote.
    \n`regionvote` - Post a vote for the region for this session's custom games.
    \n`password <password> <minutes>` - Post a countdown to the <password> release of <minutes> minutes. Automatically posts password to #mods and #super-secret-sub-club.
    \n`setvoicelimit` - Change all voice channel sizes.
    \n`clear <number>` - Remove <number> of CustomsBot messages from #custom-games. `clear all` will remove all CustomsBot messages.
    '''
    em = discord.Embed(title="CustomsBot commands", description= list_of_commands)

    await client.send_message(command_channel, embed=em)

# Keys are the commands used by helpers, values are the function names.
command_list = {
    'help': help_list,
    'squadvote': squad_vote,
    'sqv': squad_vote,
    'regionvote': region_vote,
    'rv': region_vote,
    'password': password_countdown,
    'setvoicelimit': set_voice_limit,
    'clear': remove_messages
}

# Debugging suppresses #mods and #super-secret-sub-club messages and
# treats #bot-testing in SamWalton's Discord server as both #custom-games
# and #custom-hosters.
debug = False

if debug == True:
    token_file = 'test_bot_token'
else:
    token_file = 'bot_token'

with open(token_file) as f:
    token = f.readline().strip()

client.run(token)
