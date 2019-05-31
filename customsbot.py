import discord
from discord.ext import commands
import asyncio
import datetime
import random
import os
import json
from collections import OrderedDict
from twitch import TwitchClient

file_path = os.path.dirname(__file__)

config_path = os.path.join(file_path, 'config.json')
config_data = json.load(open(config_path))

discord_client = commands.Bot(command_prefix='$')
twitch_client = TwitchClient(client_id= config_data["twitchClientID"])

#Checks if the logs folder exists, creates it if not.
log_folder = os.path.join(file_path,"logs")
folder_exists = os.path.isdir(log_folder)
if not folder_exists:
        os.mkdir(log_folder)

# Stop inbuilt $help overriding ours.
discord_client.remove_command('help')

bot_text_path = os.path.join(file_path,'bot_text.json')
text_data = json.load(open(bot_text_path))

def hoster_only():
    """
    Trust commands from #custom-hosters only. Everyone in that channel
    is a moderator or host, so anyone sending commands here is legitimate.
    """
    def predicate(ctx):
        customs_channel = get_custom_games()
        hoster_channel = discord_client.get_channel(
            config_data["channels"]["hoster"])

        return ctx.message.channel == hoster_channel
    return commands.check(predicate)

async def twitch_check(previous_presence=None):
    """
    Every 5 minutes (300 sec), check the pubgreddit Twitch channel.
    If we get any data back, the stream is live; None means it isn't.
    """
    while True:
        pubgreddit_stream = twitch_client.streams.get_stream_by_user(
            '153910806')

        if pubgreddit_stream is not None:
            game_presence = discord.Game(name="Custom games",
                                         url="https://twitch.tv/pubgreddit",
                                         type=1)
        else:
            game_presence = discord.Game(name="See #custom-games-info for info")

        #Only update the presence if it changed since last time
        if previous_presence != game_presence:
            await discord_client.change_presence(game=game_presence)

        previous_presence = game_presence

        await asyncio.sleep(300)

def get_custom_games():
    """Returns #custom-games channel object"""
    customs_channel = discord_client.get_channel(
        config_data["channels"]["customgames"])

    return customs_channel

def log_command(message_object, text, error=False):
    """Whenever a command is sent, log it to today's log file"""
    log_path = os.path.join(file_path, 'logs')
    file_name = datetime.datetime.now().strftime("%Y%m%d") + ".txt"

    logfile = os.path.join(log_path, file_name)

    if error:
        status = "| Incorrect command"
    else:
        status = ""

    with open(logfile, "a") as file:
        log_string = "{} | {} | {}#{} {}\n"
        log_string = log_string.format(str(message_object.timestamp),
                                       text,
                                       message_object.author.name,
                                       message_object.author.discriminator,
                                       status)
        file.write(log_string)

def most_reactions(message, num_only=False):
    """
    Given a message, determine which reaction emoji received the
    most votes. Breaks ties with a random choice.
    """
    reaction_emojis, reaction_count = [], []
    if num_only:
        message.reactions = [i for i in message.reactions if type(i.emoji) == str]

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

def get_custom_role():
    pubg_server = discord_client.get_server(config_data["serverID"])
    custom_role_id = config_data["customRoleID"]
    return discord.utils.get(pubg_server.roles, id=custom_role_id)

def get_user_member(user):
    pubg_server = discord_client.get_server(config_data["serverID"])
    pubg_member = pubg_server.get_member(user.id)
    return pubg_member

def has_custom_role(user):

    member_roles = get_user_member(user).roles

    has_role = False
    for role in member_roles:
        if role == get_custom_role():
            has_role = True
            break

    return has_role

async def add_custom_role(user):
    """
    Add custom role to a user if they don't already have it.
    Returns True if role was newly added.
    """

    if has_custom_role(user):
        return False
    else:
        custom_role = get_custom_role()
        user_member = get_user_member(user)
        await discord_client.add_roles(user_member, custom_role)
        return True

async def remove_custom_role(user):
    """
    Remove custom role from a user if they have it.
    Returns True if role was removed.
    """

    if has_custom_role(user):
        custom_role = get_custom_role()
        user_member = get_user_member(user)
        await discord_client.remove_roles(user_member, custom_role)
        return True
    else:
        return False

@discord_client.event
async def on_ready():

    print('Logged in as', discord_client.user.name)
    print('\nLogged in to the following servers:')
    for server in discord_client.servers:
        print(server.name)
    print('-----')

    await twitch_check()

@discord_client.event
async def on_message(message):
    # Handle DMs to the bot
    if message.server is None and not message.author.bot:
            await parse_pm(message)
    else:
        # Case insensitive commands. We have to make sure the rest of
        # the command isn't lower case so as not to alter passwords.
        # Since we're taking additional actions on raw input messages,
        # we do a quick check that this is actually a command attempt
        # so as not to needlessly process every server message.
        if message.content.startswith("$"):
            message_split = message.content.split(" ")
            message_joined = message_split[0].lower() + " " + " ".join(message_split[1:])
            print(message_joined)
            message.content = message_joined

        # Since we're overriding default on_message behaviour for the
        # commands extension, this line is required.
        await discord_client.process_commands(message)

@discord_client.event
async def on_socket_raw_receive(raw_msg):
    """
    For adding roles based on reaction.
    discord.py async release can only use on_reaction_add() to monitor
    reactions to messages in its cache (i.e. sent recently, while it is
    online). Rewrite has on_raw_reaction_add() which removes this limitation,
    but for async this is the best solution.
    """
    if not isinstance(raw_msg, str):
        return
    msg = json.loads(raw_msg)
    type = msg.get("t")
    data = msg.get("d")
    if not data:
        return

    message_id = data.get("message_id")
    if message_id == config_data["reactionMessageID"]:
        user_id = data.get("user_id")
        if type == "MESSAGE_REACTION_ADD":
            user = await discord_client.get_user_info(user_id)
            await add_custom_role(user)
        elif type == "MESSAGE_REACTION_REMOVE":
            user = await discord_client.get_user_info(user_id)
            await remove_custom_role(user)

async def parse_pm(message_object):
    """
    When users send a DM to the bot, first check if they sent any
    before now. If not, first send instructions. Otherwise, parse
    whatever command they sent.
    """

    pm_commands = ['role', 'schedule', 'twitch', 'forms', 'remove']
    pm_response = text_data["pmResponses"]["primary"]
    pm_channel = message_object.channel

    dm_content = message_object.content.lower()

    num_pms = 0
    async for _ in discord_client.logs_from(pm_channel, limit=2):
        num_pms += 1

    if num_pms > 1:
        if dm_content in pm_commands:
            if dm_content == 'role':
                role_added = await add_custom_role(message_object.author)
                if role_added:
                    pm_text = text_data["pmResponses"]["roleSuccess"]
                    log_text = "role | DM | granted new role"
                else:
                    pm_text = text_data["pmResponses"]["rolePresent"]
                    log_text = "role | DM"
            elif dm_content == 'remove':
                role_removed = await remove_custom_role(message_object.author)
                if role_removed:
                    pm_text = text_data["pmResponses"]["removeSuccess"]
                    log_text = "remove | DM | removed role"
                else:
                    pm_text = text_data["pmResponses"]["removeFailure"]
                    log_text = "remove | DM"
            else:
                pm_text = text_data["pmResponses"][dm_content]
                log_text = message_object.content + "| DM"

            await discord_client.send_message(pm_channel, content=pm_text)
            log_command(message_object, log_text)

        else:
            error_message = "Sorry, I don't recognise that command."
            await discord_client.send_message(pm_channel, content=error_message)
            log_command(message_object, message_object.content + " | DM", error=True)

    else:
        await discord_client.send_message(pm_channel, content=pm_response)
        log_command(message_object, "Sent instructions | DM")

@discord_client.command(name='squadvote', aliases=['sqv'], pass_context=True)
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
                await discord_client.send_message(message_channel,
                                          content= error_message)
                return

            squads_correct_range = all(i >= 1 and i <= 10
                                       for i in squad_sizes_selected)
            if not squads_correct_range:
                error_message = ("Error: Please only use integers"
                                 " between 1 and 10 for `squadvote`.")
                await discord_client.send_message(message_channel,
                                          content= error_message)
                return

    customs_channel = get_custom_games()

    squad_vote_message = ("Please vote on squad size for the next game:"
                          "\nTimer: {}")
    default_message = squad_vote_message.format("02:00")
    
    sent_squad_message = await discord_client.send_message(customs_channel,
                                                   content= default_message)

    for squad_size_int in squad_sizes_selected:
        if squad_size_int == 10:
            emoji = "\U0001F51F"  # :keycap_ten: is a single emoji
        else:
            emoji = str(squad_size_int) + "\U000020E3"

        await discord_client.add_reaction(sent_squad_message, emoji)

    here_ping = await discord_client.send_message(customs_channel,
                                          content="@here")

    await discord_client.send_message(message_channel,
                              content= "Squad size vote successfully posted.")
    log_command(message_object, "Squad vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = squad_vote_message.format(countdown_timer_string)
        await discord_client.edit_message(sent_squad_message, new_message)

    sent_squad_message = await discord_client.get_message(customs_channel,
                                                  sent_squad_message.id)
    await discord_client.clear_reactions(sent_squad_message)

    squad_selected = most_reactions(sent_squad_message, num_only=True)

    squad_result = squad_selected + "P Squads"

    squad_message_finished = "Squad size vote over. Result: {}".format(squad_result)

    await discord_client.edit_message(sent_squad_message, squad_message_finished)

    await discord_client.delete_message(here_ping)

    if len(squad_selected) > 1:
        voice_limit_int = int(squad_selected[:-1])  # Unicode to int
    else:
        voice_limit_int = 10

    await ctx.invoke(set_voice_limit, user_limit=voice_limit_int)

@discord_client.command(name='regionvote', aliases=['rv'], pass_context=True)
@hoster_only()
async def region_vote(ctx):
    """
    Starts a vote on region to host on.

    Hoster has no control over this one; it just adds every region's emoji
    and determines the winner.
    """
    region_emoji_ids = config_data["regionEmojis"]


    customs_channel = get_custom_games()

    region_vote_message = ("Which region should we host today's games on?"
                           "\nTimer: {}")
    default_region_message = region_vote_message.format("02:00")
    region_message = await discord_client.send_message(customs_channel,
                                               content= default_region_message)

    for region_emoji in region_emoji_ids:
        region_emoji_obj = discord.utils.get(discord_client.get_all_emojis(),
                                             id=region_emoji)
        await discord_client.add_reaction(region_message, region_emoji_obj)

    here_ping = await discord_client.send_message(customs_channel,
                                          content="@here")

    message_channel = ctx.message.channel
    await discord_client.send_message(message_channel,
                              "Region vote successfully posted.")
    log_command(ctx.message, "Region vote")
    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = region_vote_message.format(countdown_timer_string)
        await discord_client.edit_message(region_message, new_message)

    region_message = await discord_client.get_message(customs_channel,
                                              region_message.id)
    await discord_client.clear_reactions(region_message)
    region_selected = most_reactions(region_message)

    region_result = region_selected

    region_message_finished = "Region vote over. Result: {}".format(region_result)

    await discord_client.delete_message(here_ping)

    await discord_client.edit_message(region_message, region_message_finished)

@discord_client.command(name='mapvote', aliases=['mv'], pass_context=True)
@hoster_only()
async def map_vote(ctx, *args):
    """
    Starts a vote on which Map to play.

    The hoster can specify which maps to vote, or 'all' to include
    every map. The vote stays open for 2 minutes.
    """
    message_object = ctx.message
    message_channel = ctx.message.channel
    message_maps_choice = args
    maps_for_vote = "" 
    emojis = ""
    map_choice_selected = ""
    maps_available = ['Erangel', 'Miramar', 'Sanhok', 'Vikendi', 'Camp Jackal']

    if len(message_maps_choice) == 0:
        map_choice_selected = maps_available
        emojis = ['\U0001F3DE','\U0001F3DC','\U0001F3DD','\U0001F3D4']
        maps_for_vote = ("\nErangel = \U0001F3DE"
                         "\nMiramar = \U0001F3DC"
                         "\nSanhok = \U0001F3DD"
                         "\nVikendi = \U0001F3D4")
    
    #if any(s in message_maps_choice for s in maps_available):
    #    pass
    #else:
    #    maps = " ".join(maps_available)
    #    error_message = ("Error: Can't find one or more maps. \nMaps available are: ") + maps
    #    await discord_client.send_message(message_channel, content=error_message)
    #    return

    if 'Erangel' in message_maps_choice:
        map_choice_selected = map_choice_selected + "Erangel"
        emojis = emojis + "\U0001F3DE"
        maps_for_vote = maps_for_vote + "\nErangel: \U0001F3DE"
    if 'Miramar' in message_maps_choice:
        map_choice_selected = map_choice_selected + "Miramar"
        emojis = emojis + "\U0001F3DC"
        maps_for_vote = maps_for_vote + "\nMiramar: \U0001F3DC"
    if 'Sanhok' in message_maps_choice:
        map_choice_selected = map_choice_selected + "Sanhok"
        emojis = emojis + "\U0001F3DD"
        maps_for_vote = maps_for_vote + "\nSanhok: \U0001F3DD"
    if 'Vikendi' in message_maps_choice:
        map_choice_selected = map_choice_selected + "Vikendi"
        emojis = emojis + "\U0001F3D4"
        maps_for_vote = maps_for_vote + "\nVikendi: \U0001F3D4"
    if 'Jackal' in message_maps_choice:
        map_choice_selected = map_choice_selected + "Camp Jackal"
        emojis = emojis + "\U0001F304"
        maps_for_vote = maps_for_vote + "\nCamp Jackal: \U0001F304"

    
    customs_channel = get_custom_games()

    maps_vote_message = ("Please vote on which map you want to play for the next game:") + maps_for_vote + ("\nTimer: {}")
    default_message = maps_vote_message.format("02:00")
    
    sent_map_message = await discord_client.send_message(customs_channel,
                                                   content= default_message)

    for emoji in emojis:
        await discord_client.add_reaction(sent_map_message, emoji)

    here_ping = await discord_client.send_message(customs_channel,
                                          content="@here")

    await discord_client.send_message(message_channel,
                              content= "Map vote successfully posted." + maps_for_vote)
    log_command(message_object, "Map vote")

    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = maps_vote_message.format(countdown_timer_string)
        await discord_client.edit_message(sent_map_message, new_message)

    sent_map_message = await discord_client.get_message(customs_channel,
                                                  sent_map_message.id)
    await discord_client.clear_reactions(sent_map_message)

    map_selected = most_reactions(sent_map_message)

    map_result = map_selected

    map_message_finished = "Map vote over. Result: {}".format(map_result)

    await discord_client.edit_message(sent_map_message, map_message_finished)
    await discord_client.send_message(message_channel, map_message_finished)
    await discord_client.delete_message(here_ping)

@discord_client.command(name='perspectivevote', aliases=['pv'], pass_context=True)
@hoster_only()
async def perspective_vote(ctx):
    """
    Starts a vote on perspective for the game mode.

    """

    customs_channel = get_custom_games()

    perspective_vote_message = ("Which perspective should the next game be played on?"
                           "\nTimer: {}")
    default_perspective_message = perspective_vote_message.format("02:00")
    perspective_message = await discord_client.send_message(customs_channel,
                                               content= default_perspective_message)
    perspective_emojis = ['1','3']
    
    for perspective_int in perspective_emojis:
        emoji = str(perspective_int) + "\U000020E3"
        await discord_client.add_reaction(perspective_message, emoji)
    here_ping = await discord_client.send_message(customs_channel,
                                          content="@here")

    message_channel = ctx.message.channel
    await discord_client.send_message(message_channel,
                              "Perspective vote successfully posted.")
    log_command(ctx.message, "Perspective vote")
    time_to_post = datetime.datetime.now() + datetime.timedelta(seconds=120)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = perspective_vote_message.format(countdown_timer_string)
        await discord_client.edit_message(perspective_message, new_message)

    perspective_message = await discord_client.get_message(customs_channel,
                                              perspective_message.id)
    await discord_client.clear_reactions(perspective_message)
    perspective_selected = most_reactions(perspective_message)

    perspective_result = perspective_selected

    perspective_message_finished = "Perspective vote over. Result: {}".format(perspective_result)

    await discord_client.delete_message(here_ping)

    await discord_client.edit_message(perspective_message, perspective_message_finished)


@discord_client.command(name='password', pass_context=True)
@hoster_only()
async def password_countdown(ctx, password, *args):
    """
    Starts a countdown to password release in #custom-games. Immediately
    posts server name and password to #super-secret-sub-club,
    pinging @here in SSSC only.

    Hoster must specify a password, and may optionally specify the number
    of minutes until the password is released. Defaults to 2 minutes.
    """
    message_channel = ctx.message.channel

    if not password:
        error_message = "Error: Please enter a password."
        await discord_client.send_message(message_channel, content=error_message)
        return

    if len(args) == 0:
        num_seconds = 120
    elif len(args) == 1:
        try:
            num_seconds = int(args[0])*60
        except ValueError:
            error_message = ("Error: Please use an integer to denote the "
                             "countdown length for `password`.")
            await discord_client.send_message(message_channel, content=error_message)
            return
    else:
        error_message = ("Error: Too many arguments.")
        await discord_client.send_message(message_channel, content=error_message)
        return

    customs_channel = get_custom_games()

    current_time = datetime.datetime.now()
    time_to_post = current_time + datetime.timedelta(seconds=num_seconds)
    countdown_timer = time_to_post - datetime.datetime.now()
    countdown_timer_string = get_countdown_string(countdown_timer)

    template_string = "Server name: PUBG Reddit\nPassword: {}"

    default_text = template_string.format("[" + countdown_timer_string + "]")
    result_string = template_string.format(password)

    countdown_message = await discord_client.send_message(customs_channel,
                                                  default_text)

    # Send password to SSSC channel first
    sssc_channel = discord_client.get_channel(config_data["channels"]["sssc"])
    await discord_client.send_message(sssc_channel, result_string)
    await discord_client.send_message(sssc_channel, content="@here")

    log_command(ctx.message, "Password")

    # Password timer for custom-games channel
    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        string_bracketed = "[" + countdown_timer_string + "]"
        new_message = template_string.format(string_bracketed)
        await discord_client.edit_message(countdown_message, new_message)

    await discord_client.edit_message(countdown_message, result_string)
    await discord_client.send_message(customs_channel, content="@here")

@discord_client.command(name='countdown', pass_context=True)
@hoster_only()
async def countdown_timer(ctx, *args):
    """
    Starts a countdown to when the game will begin, in #custom-games.
    
    Hoster must start the game once countdown has hit 00:00 or "Game Started".

    Default time: 2 minutes
    """
    message_channel = ctx.message.channel

    if len(args) == 0:
        num_seconds = 120
    elif len(args) == 1:
        try:
            num_seconds = int(args[0])*60
        except ValueError:
            error_message = ("Error: Please use an integer to denote the "
                             "countdown length.")
            await discord_client.send_message(message_channel, content=error_message)
            return
    else:
        error_message = ("Error: Too many arguments.")
        await discord_client.send_message(message_channel, content=error_message)
        return

    customs_channel = get_custom_games()

    current_time = datetime.datetime.now()
    time_to_post = current_time + datetime.timedelta(seconds=num_seconds)
    countdown_timer = time_to_post - datetime.datetime.now()
    countdown_timer_string = get_countdown_string(countdown_timer)

    template_string = "The next game will begin in: {}"

    default_text = template_string.format(countdown_timer_string)

    countdown_message = await discord_client.send_message(customs_channel,
                                                  default_text)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = template_string.format(countdown_timer_string)
        await discord_client.edit_message(countdown_message, new_message)

    await discord_client.delete_message(countdown_message)
    await discord_client.send_message(customs_channel, content="Game Started!")

@discord_client.command(name='timer', pass_context=True)
@hoster_only()
async def timer(ctx, *args):
    """
    Starts a timer in #custom-games.

    Default time: 2 minutes
    """
    message_channel = ctx.message.channel

    if len(args) == 0:
        num_seconds = 120
    elif len(args) == 1:
        try:
            num_seconds = int(args[0])*60
        except ValueError:
            error_message = ("Error: Please use an integer to denote the "
                             "timer length.")
            await discord_client.send_message(message_channel, content=error_message)
            return
    else:
        error_message = ("Error: Too many arguments.")
        await discord_client.send_message(message_channel, content=error_message)
        return

    customs_channel = get_custom_games()

    current_time = datetime.datetime.now()
    time_to_post = current_time + datetime.timedelta(seconds=num_seconds)
    timer = time_to_post - datetime.datetime.now()
    timer_string = get_countdown_string(timer)

    template_string = "A timer has started!\n{}"

    default_text = template_string.format(timer_string)

    timer_message = await discord_client.send_message(customs_channel,
                                                  default_text)

    while datetime.datetime.now() < time_to_post:
        countdown_timer = time_to_post - datetime.datetime.now()
        countdown_timer_string = get_countdown_string(countdown_timer)
        await asyncio.sleep(1)
        new_message = template_string.format(countdown_timer_string)
        await discord_client.edit_message(timer_message, new_message)

    await discord_client.delete_message(timer_message)
    await discord_client.send_message(customs_channel, content="Time's Up!")

@discord_client.command(name='setvoicelimit', pass_context=True)
@hoster_only()
async def set_voice_limit(ctx, user_limit):
    """
    Changes all custom games voice channel sizes to the one specified.

    Can be run either directly via $setvoicelimit or indirectly in
    other functions.
    """
    message_channel = ctx.message.channel

    try:
        voice_limit_int = int(user_limit)
    except ValueError:
        error_message = ("Error: Please use an integer to denote "
                         "the size of voice channels.")  
        await discord_client.send_message(message_channel, content=error_message)
        return

    all_channels = discord_client.get_all_channels()
    for channel in all_channels:
        server_check = channel.server == discord_client.get_server(
            config_data["serverID"])

        if channel.name.startswith("\U0001F6E0") and server_check:
            await discord_client.edit_channel(channel, user_limit=voice_limit_int)

    voice_limit_message = "Set custom games voice channels to new user limit of {}."
    voice_message = voice_limit_message.format(voice_limit_int)

    await discord_client.send_message(message_channel, content=voice_message)

@discord_client.command(name='clear', pass_context=True)
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
            await discord_client.send_message(message_channel,
                                              content=error_message)
            return
    
    customs_channel = get_custom_games()

    message_count = 0
    messages_to_remove = []

    bot_id = config_data["botID"]

    # Defaults to only retrieving 100 messages from #custom-games.
    # Has the potential to cause an issue, but should rarely ever do so.
    async for message in discord_client.logs_from(customs_channel):
        if message.author.id == bot_id:
            if num_messages == 'all':
                messages_to_remove.append(message)
            else:
                messages_to_remove.append(message)
                message_count += 1
                if message_count == num_messages:
                    break

    for customsbot_message in messages_to_remove:
        await discord_client.delete_message(customsbot_message)

    confirmation_text = "Removed {} CustomsBot messages from #custom-games."
    confirmation_text = confirmation_text.format(num_messages)
    await discord_client.send_message(message_channel, confirmation_text)

    log_command(ctx.message, "Remove messages ({})".format(num_messages))

@discord_client.command(name='help', pass_context=True)
@hoster_only()
async def help(ctx):
    hoster_channel = ctx.message.channel

    help_text = "\n\n".join(text_data["helpText"])

    help_embed = discord.Embed(title="CustomsBot available commands",
                               description=help_text)

    await discord_client.send_message(hoster_channel, embed=help_embed)

@discord_client.command(name='schedule', pass_context=True)
async def schedule(ctx):
    schedule_text = text_data["chatResponses"]["schedule"]
    message_channel = ctx.message.channel
    await discord_client.send_message(message_channel, content=schedule_text)
    await discord_client.delete_message(ctx.message)
    log_command(ctx.message, "Schedule info posted")

@discord_client.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        message_channel = ctx.message.channel
        await discord_client.send_message(message_channel,
                                  content= 'Required argument(s) missing.')
    else:
        print(error)

discord_client.run(config_data["botToken"])
