import discord
import asyncio
import datetime
import random

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as', client.user.name)
    print('\nLogged in to the following servers:')
    for server in client.servers:
        print(server.name)
    print('-----')

@client.event
async def on_message(message):
    is_command = message.content.startswith('$')

    if is_command:
        customs_channel = get_custom_games()
        message_channel = message.channel
        if message_channel == customs_channel['hosters']:
            await parse_command(message)
        else:
            error_message = "Error: You must be in the #custom-hosters channel to do that."
            await client.send_message(message_channel, content=error_message)

def get_custom_games():
    customs_hosters = client.get_channel(str(375276183777968130))  # Live
    customs_channel = client.get_channel(str(317770788524523531))  # Live

    if debug:
        customs_hosters = client.get_channel(str(382550498533703680))  # bot-testing in my server
        customs_channel = customs_hosters  # Test in the same channel.

    channels = {'hosters': customs_hosters, 'games': customs_channel}

    return channels

def log_command(message_object, text):
    print(message_object.timestamp, "| COMMAND |", text, "|", message_object.author.name)

async def parse_command(message_object):

    command_string = message_object.content
    command_channel = message_object.channel

    split_command = command_string[1:].split(" ")
    primary_command = split_command[0].lower()
    options = split_command[1:]

    if primary_command in command_list:
        result = await command_list[primary_command](message_object)
    else:
        print("INCORRECT COMMAND |", primary_command, "|", message_object.author.name)
        result = "Error: That command doesn't exist. To see a list of available commands type $help."

    if result:
        await client.send_message(command_channel, content=result)

async def squad_vote(command_message):
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
    default_message = squad_vote_message.format("03:00")
    
    sent_squad_message = await client.send_message(customs_channel['games'], content= default_message)

    for squad_size_int in squad_sizes_selected:
        if squad_size_int == 10:
            emoji = "\U0001F51F"  # :keycap_ten: is a single emoji
        else:
            emoji = str(squad_size_int) + "\U000020e3"

        await client.add_reaction(sent_squad_message, emoji)

    await client.send_message(customs_channel['games'], content="@here")

    message_channel = command_message.channel
    await client.send_message(message_channel, "Squad size vote successfully posted.")
    log_command(command_message, "Squad vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=180)

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

    await set_voice_limit(user_limit=squad_selected)

def most_reactions(message):
    message_reactions = message.reactions
    reaction_emojis, reaction_count = [], []
    for message_reaction in message_reactions:
        reaction_emojis.append(message_reaction.emoji)
        reaction_count.append(message_reaction.count)

    max_emoji = [reaction_emojis[i] for i,x in enumerate(reaction_count) if x == max(reaction_count)]
    num_emojis = len(max_emoji)

    if num_emojis == 1:
        return max_emoji[0]
    else:
        i = random.randint(0,num_emojis-1)
        return max_emoji[i]

async def region_vote(command_message):
    regions = [
               333366981959090186,  # Asia
               333366950455672833,  # EU
               379707501282590720,  # KJP
               333366997729411082,  # NA
               333366933657223168,  # OCE
               333366961792876544,  # SA
               333366971586445313,  # SEA
               ]

    customs_channel = get_custom_games()

    region_vote_message = "Which region should we host today's games on?\nTimer: {}"
    default_region_message = region_vote_message.format("03:00")
    sent_region_message = await client.send_message(customs_channel['games'], content= default_region_message)

    for region_emoji in regions:
        region_emoji_obj = discord.utils.get(client.get_all_emojis(), id=str(region_emoji))
        await client.add_reaction(sent_region_message, region_emoji_obj)

    await client.send_message(customs_channel['games'], content="@here")

    message_channel = command_message.channel
    await client.send_message(message_channel, "Region vote successfully posted.")
    log_command(command_message, "Region vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=180)

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
    await client.edit_message(sent_region_message, region_message_finished)

def get_countdown_string(timedelta_object):
    countdown_timer_split = str(timedelta_object).split(":")
    countdown_timer_string = ":".join(countdown_timer_split[1:])
    return countdown_timer_string.split(".")[0]  # Without decimal

async def password_countdown(command_message):
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

    mods_channel = client.get_channel(str(340575221495103498))
    sssc_channel = client.get_channel(str(340984090109018113))
    
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
    async for message in client.logs_from(customs_channel['games']):
        if message.author.id == str(399360578956689409):
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
    command_channel = command_message.channel
    list_of_commands = '''
    `squadvote <squad size 1> <squad size 2> ...` - Post a vote for squad size for the next game, defaults to 1, 2, 4, and 8. `squadvote all` will do every size between 1 and 10. Automatically changes voice channel sizes to winning vote.
    \n`regionvote` - Post a vote for the region for this session's custom games.
    \n`password <password> <minutes>` - Post a countdown to the <password> release of <minutes> minutes.
    \n`setvoicelimit` - Change all voice channel sizes.
    \n`clear <number>` - Remove <number> of CustomsBot messages from #custom-games. `clear all` will remove all CustomsBot messages.
    '''
    em = discord.Embed(title="CustomsBot commands", description= list_of_commands)

    await client.send_message(command_channel, embed=em)

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

debug = True

with open('bot_token') as f:
    token = f.readline().strip()

client.run(token)
