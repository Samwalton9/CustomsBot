import discord
from discord.ext import commands
import asyncio
import datetime
import random
import os
import json

client = commands.Bot(command_prefix='$')

"""Checks if the logs folder exists, creates it if not."""
folder_exists = os.path.isdir("logs")
if not folder_exists:
        os.mkdir("logs")

# Stop inbuilt $help overriding ours.
client.remove_command('help')

def hoster_only():
    """Trust commands from #custom-hosters only"""
    def predicate(ctx):
        customs_channel = get_custom_games()
        if debug:
            hoster_channel = client.get_channel("382550498533703680")
        else:
            hoster_channel = client.get_channel("375276183777968130")
        return ctx.message.channel == hoster_channel
    return commands.check(predicate)

def get_custom_games():
    """Returns #custom-games object"""
    customs_channel = client.get_channel('317770788524523531')

    if debug:
        # bot-testing in my server
        customs_channel = client.get_channel('382550498533703680')

    return customs_channel

def log_command(message_object, text, error=False):
    """Whenever a command is sent, log it to today's log file"""
    current_folder = os.path.dirname(__file__)
    file_path = os.path.join(current_folder, 'logs')
    file_name = datetime.datetime.now().strftime("%Y%m%d") + ".txt"

    logfile = os.path.join(file_path, file_name)

    if error:
        status = " | Incorrect command"
    else:
        status = ""

    with open(logfile, "a") as file:
        log_string = "{} | {} | {}#{} {} \n"
        log_string = log_string.format(str(message_object.timestamp),
                                       text,
                                       message_object.author.name,
                                       message_object.author.discriminator,
                                       status)
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

    max_emoji = [reaction_emojis[i] for i,x in enumerate(reaction_count)
                 if x == max(reaction_count)]

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
    # Handle DMs to the bot
    if message.server is None and "CustomsBot" not in message.author.name:
        await parse_pm(message)
    else:
        # Since we're overriding default on_message behaviour for the
        # commands extension, this line is required.
        await client.process_commands(message)

async def parse_pm(message_object):
    data = json.load(open('bot_text.json'))

    pm_commands = ['role', 'schedule', 'twitch', 'forms']
    pm_response = data["pmResponses"]["primary"]
    pm_channel = message_object.channel
    full_username = message_object.author.name + "#" + message_object.author.discriminator

    num_pms = 0
    async for pm_message in client.logs_from(pm_channel, limit=2):
        num_pms += 1

    if num_pms > 1:
        if message_object.content in pm_commands:
            if message_object.content == 'role':
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
                        pm_text = data["pmResponses"]["rolePresent"]
                        log_text = message_object.content + " | DM"
                    else:
                        custom_role = discord.utils.get(pubg_server.roles, id=custom_role_id)
                        await client.add_roles(pubg_member, custom_role)
                        pm_text = data["pmResponses"]["roleSuccess"]
                        log_text = message_object.content + " | DM | granted new role"

                    log_command(message_object, log_text)

                else:
                    print("Role assignment is not available in debug mode.")
                    pm_text = None                    

            else:
                pm_text = data["pmResponses"][message_object.content]
            
            if pm_text:
                await client.send_message(pm_channel, content=pm_text)
        else:
            log_command(message_object, message_object.content + " | DM", error=True)
            error_message = "Sorry, I don't recognise that command."
            await client.send_message(pm_channel, content=error_message)
    else:
        print("Sent instructions to", message.author.name)
        await client.send_message(pm_channel, content=pm_response)

@client.command(name='squadvote', aliases=['sqv'], pass_context=True)
@hoster_only()
async def squad_vote(ctx, *args):
    """
    Starts a vote on squad size.

    The hoster can specify squad sizes to be used, or 'all' to include
    every size between 1 and 10. If there are no arguments, the vote
    defaults to 1, 2, 4, and 8. The vote stays open for 2 minutes.

    Once a winner is determined, set_voice_limit() is run for the
    winning size.
    """
    message_object = ctx.message
    message_channel = ctx.message.channel
    command_sent = message_object.content
    message_squad_sizes = args
    
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
                error_message = ("Error: Please only use integers"
                                 " as arguments for `squadvote`.")
                await client.send_message(message_channel,
                                          content= error_message)
                return

            squads_correct_range = all(i >= 1 and i <= 10
                                       for i in squad_sizes_selected)
            if not squads_correct_range:
                error_message = ("Error: Please only use integers"
                                 " between 1 and 10 for `squadvote`.")
                await client.send_message(message_channel,
                                          content= error_message)
                return

    customs_channel = get_custom_games()

    squad_vote_message = ("Please vote on squad size for the next game:"
                          "\nTimer: {}")
    default_message = squad_vote_message.format("02:00")
    
    sent_squad_message = await client.send_message(customs_channel,
                                                   content= default_message)

    for squad_size_int in squad_sizes_selected:
        if squad_size_int == 10:
            emoji = "\U0001F51F"  # :keycap_ten: is a single emoji
        else:
            emoji = str(squad_size_int) + "\U000020e3"

        await client.add_reaction(sent_squad_message, emoji)

    here_ping = await client.send_message(customs_channel,
                                          content="@here")

    await client.send_message(message_channel,
                              content= "Squad size vote successfully posted.")
    log_command(message_object, "Squad vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = squad_vote_message.format(countdown_timer_string)
        await client.edit_message(sent_squad_message, new_message)

    sent_squad_message = await client.get_message(customs_channel,
                                                  sent_squad_message.id)
    await client.clear_reactions(sent_squad_message)

    squad_selected = most_reactions(sent_squad_message)

    squad_result = squad_selected + "P Squads"

    squad_message_finished = "Squad size vote over. Result: {}".format(squad_result)

    await client.edit_message(sent_squad_message, squad_message_finished)

    await client.delete_message(here_ping)

    if len(squad_selected) > 1:
        voice_limit_int = int(squad_selected[:-1])  # Unicode to int
    else:
        voice_limit_int = 10

    await set_voice_limit(ctx, user_limit=voice_limit_int)

@client.command(name='regionvote', aliases=['rv'], pass_context=True)
@hoster_only()
async def region_vote(ctx):
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

    region_vote_message = ("Which region should we host today's games on?"
                           "\nTimer: {}")
    default_region_message = region_vote_message.format("02:00")
    region_message = await client.send_message(customs_channel,
                                               content= default_region_message)

    if debug:
        debug_text = "[Regions added]"
        await client.send_message(customs_channel, debug_text)
    else:
        for region_emoji in region_emoji_ids:
            region_emoji_obj = discord.utils.get(client.get_all_emojis(),
                                                 id=region_emoji)
            await client.add_reaction(region_message, region_emoji_obj)

    here_ping = await client.send_message(customs_channel,
                                          content="@here")

    message_channel = ctx.message.channel
    await client.send_message(message_channel,
                              "Region vote successfully posted.")
    log_command(ctx.message, "Region vote")
    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = region_vote_message.format(countdown_timer_string)
        await client.edit_message(region_message, new_message)

    region_message = await client.get_message(customs_channel,
                                              region_message.id)
    await client.clear_reactions(region_message)
    region_selected = most_reactions(region_message)

    region_result = region_selected

    region_message_finished = "Region vote over. Result: {}".format(region_result)

    await client.delete_message(here_ping)

    await client.edit_message(region_message, region_message_finished)

@client.command(name='password', pass_context=True)
@hoster_only()
async def password_countdown(ctx, password, timer):
    """
    Starts a countdown to password release in #custom-games. Immediately
    posts server name and password to #mods and #super-secret-sub-club,
    pinging @here in SSSC only.

    Hoster must specify a password, and may optionally specify the number
    of minutes until the password is released. Defaults to 5 minutes.
    """
    message_channel = ctx.message.channel

    if not password:
        error_message = "Error: Please enter a password."
        await client.send_message(message_channel, content=error_message)
        return

    if timer:
        try:
            num_seconds = int(timer)*60
        except ValueError:
            error_message = ("Error: Please use an integer to denote the "
                             "countdown length for `password`.")
            await client.send_message(message_channel, content=error_message)
            return
    else:
        num_seconds = 300

    customs_channel = get_custom_games()

    current_time = datetime.datetime.now()
    time_to_post = current_time + datetime.timedelta(seconds=num_seconds)
    countdown_timer = time_to_post - datetime.datetime.now()
    countdown_timer_string = get_countdown_string(countdown_timer)

    template_string = "Server name: PUBG Reddit\nPassword: {}"

    default_text = template_string.format("[" + countdown_timer_string + "]")
    result_string = template_string.format(password)

    countdown_message = await client.send_message(customs_channel,
                                                  default_text)

    if debug:
        mods_channel = client.get_channel('382550498533703680')
        sssc_channel = client.get_channel('382550498533703680')
    else:
        mods_channel = client.get_channel('340575221495103498')
        sssc_channel = client.get_channel('340984090109018113')
    
    for channel_name in [mods_channel, sssc_channel]:
        await client.send_message(channel_name, result_string)
        if channel_name == sssc_channel:
            await client.send_message(channel_name, content="@here")

    log_command(ctx.message, "Password")

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        string_bracketed = "[" + countdown_timer_string + "]"
        new_message = template_string.format(string_bracketed)
        await client.edit_message(countdown_message, new_message)

    await client.edit_message(countdown_message, result_string)
    await client.send_message(customs_channel, content="@here")

@client.command(name='setvoicelimit', pass_context=True)
@hoster_only()
async def set_voice_limit(ctx, user_limit):
    """
    Changes all custom games voice channel sizes to the one specified.

    Can be run either directly via $setvoicelimit or indirectly in
    other functions.
    """
    message_channel = ctx.message.channel

    if user_limit:
        try:
            voice_limit_int = int(user_limit)
        except ValueError:
            error_message = ("Error: Please use an integer to denote "
                             "the size of voice channels.")  
            await client.send_message(message_channel, content=error_message)
            return

    all_channels = client.get_all_channels()
    for channel in all_channels:
        if channel.name.startswith("\U0001F6E0"):
            await client.edit_channel(channel, user_limit=voice_limit_int)

    voice_limit_message = "Set custom games voice channels to new user limit of {}."
    voice_message = voice_limit_message.format(voice_limit_int)

    await client.send_message(message_channel, content=voice_message)

@client.command(name='clear', pass_context=True)
@hoster_only()
async def remove_messages(ctx, num_messages):
    """
    Removes a number of CustomsBot messages from #custom-games.

    Hosters aren't necessarily mods, so they need some way to clear
    CustomsBot's messages. This function removes either a set amount
    or all of CustomsBot's messages.
    """
    message_channel = ctx.message.channel

    if num_messages != 'all':
        try:
            num_messages = int(num_messages)
        except ValueError:
            error_message = ("Error: Please use an integer to denote the"
                             " number of messages to clear.")
            await client.send_message(message_channel, content=error_message)
            return
    
    customs_channel = get_custom_games()

    message_count = 0
    messages_to_remove = []

    if debug:
        bot_id = '400984104960655362'
    else:
        bot_id = '399360578956689409'

    # Defaults to only retrieving 100 messages from #custom-games.
    # Has the potential to cause an issue, but should rarely ever do so.
    async for message in client.logs_from(customs_channel):
        if message.author.id == bot_id:
            if num_messages == 'all':
                messages_to_remove.append(message)
            else:
                messages_to_remove.append(message)
                message_count += 1
                if message_count == num_messages:
                    break

    for customsbot_message in messages_to_remove:
        await client.delete_message(customsbot_message)

    confirmation_text = "Removed {} CustomsBot messages from #custom-games."
    confirmation_text = confirmation_text.format(num_messages)
    await client.send_message(message_channel, confirmation_text)

    log_command(ctx.message, "Remove messages ({})".format(num_messages))

@client.command(name='help', pass_context=True)
@hoster_only()
async def help(ctx):
    hoster_channel = ctx.message.channel

    data = json.load(open('bot_text.json'))

    help_text = data["helpText"]

    help_embed = discord.Embed(title="CustomsBot available commands",
                               description=help_text)

    await client.send_message(hoster_channel, embed=help_embed)

@client.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        message_channel = ctx.message.channel
        await client.send_message(message_channel,
                                  content= 'Required argument(s) missing.')

# Debugging suppresses #mods and #super-secret-sub-club messages and
# treats #bot-testing in SamWalton's Discord server as both #custom-games
# and #custom-hosters.
debug = True

if debug == True:
    token_file = 'test_bot_token'
else:
    token_file = 'bot_token'

with open(token_file) as f:
    token = f.readline().strip()

client.run(token)
