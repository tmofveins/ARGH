import discord
from discord.ext import commands
import re

import c2v
import secret
import utils

TOKEN = secret.TOKEN
client = commands.Bot(command_prefix = "!")

@client.event
async def on_ready():
    print("Bot is ready. Logged in as:")
    print(client.user.name)
    print(client.user.id)
    print("------")

#################################################

@client.command()
async def c2tier(message, *, arg):
    """
    Outputs a relevant tier list based on a level the user requests.
    """
    channel = message.channel

    if arg == '12':
        await channel.send('https://i.imgur.com/jQiHNk2.jpg')
    elif arg == '13':
        await channel.send('https://i.imgur.com/HYcgkDo.jpg')
    elif arg == '14':
        await channel.send('https://i.imgur.com/hdf3FZD.jpg')
    elif arg == '15':
        await channel.send('https://i.imgur.com/wpsrc18.jpg')

@c2tier.error 
async def c2tier_error(ctx, error):
    """
    Error handler in case user forgets to specify the difficulty level.
    """
    if isinstance(error, commands.MissingRequiredArgument):    
        await ctx.send(embed = utils.generate_embed(
                status = 'Error',
                msg = "Please also specify which level you require: 12, 13, 14 or 15."
            ))


#################################################

# initializing dataframe used for searching songs and dictionary for storing links
table = c2v.get_table(utils.SOURCE)
charts_df = c2v.get_initial_df(utils.SOURCE)

merged_dict = c2v.merge_keys_and_links(table)

merged_df = c2v.get_merged_df(charts_df, merged_dict)
merged_df.to_csv("test.csv")

#################################################

@client.command()
async def c2s(message, *, arg):
    """
    Searches ct2viewer for a song that matches closest to the user input.
    Returns an embed containing the song information and links to its charts.
    """
    channel = message.channel

    is_emote = re.search(utils.EMOTE_REGEX, arg)
    is_ping = re.search(utils.PING_REGEX, arg)    

    if is_emote or is_ping:
        await channel.send(embed = utils.generate_embed(
                status = 'Error',
                msg = 'Invalid input. Ping, emote, or channel name detected.'
            ))
        return

    result = c2v.search_song(merged_df, arg)
    embed = c2v.process_search(merged_dict, result)

    print(embed)
    print(type(embed))

    await channel.send(embed = embed)

@c2s.error 
async def c2s_error(ctx, error):
    """
    Error handler in case user forgets to specify the difficulty level.
    """
    if isinstance(error, commands.MissingRequiredArgument):    
        await ctx.send(embed = utils.generate_embed(
                status = 'Error',
                msg = "Please also specify a search key."
            ))

#################################################

@client.command()
async def c2d(message, *, arg):
    channel = message.channel

    is_emote = re.search(utils.EMOTE_REGEX, arg)
    is_ping = re.search(utils.PING_REGEX, arg) 

    if is_emote or is_ping:
        await channel.send(embed = utils.generate_embed(
                status = 'Error',
                msg = 'Invalid input. Ping, emote, or channel name detected.'
            ))
        return

    try:
        input = int(arg)
        if input in range(1, 16):
            output = c2v.search_difficulty(merged_df, input)

            for page in output:
                await channel.send(", ".join(page))

        else:
            await channel.send(embed = utils.generate_embed(
                    status = 'Error',
                    msg = 'Invalid input. Not within correct difficulty range.'
                ))
            return

    except:
        await channel.send(embed = utils.generate_embed(
                status = 'Error',
                msg = 'Invalid input. Not a number.'
            ))
        return

#################################################

client.run(TOKEN)