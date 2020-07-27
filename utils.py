import re
import discord

SOURCE = "https://ct2view.the-kitti.com/chartlist.html"
PREFIX = "https://ct2view.the-kitti.com"

# regex to detect Japanese characters + Kanji
# for the purpose of this program it doesn't really matter to distinguish mandarin/kanji input
JP_REGEX = re.compile('[\u4E00-\u9FAF]|[\u3000-\u303F]|[\u3040-\u309F]|\
                    [\u30A0-\u30FF]\|[\uFF00-\uFFEF]|[\u4E00-\u9FAF]|\
                    [\u2605-\u2606]|[\u2190-\u2195]|\u203B')

# regex to detect emotes in user input
EMOTE_REGEX = re.compile("(:[a-zA-Z0-9_\-~]+?:)")

# regex to detect pings, channel titles, or roles
PING_REGEX = re.compile("<(#|@!|@#)\d+>")

# regexes to detect which difficulty a link corresponds to
REGEXES_BY_DIFF = {
    "easy.html": re.compile("chartlist\/(.*?)\/easy"),
    "hard.html": re.compile("chartlist\/(.*?)\/hard"),
    "chaos.html": re.compile("chartlist\/(.*?)\/chaos"),
    "glitch.html": re.compile("chartlist\/(.*?)\/glitch")
}

#################################################

def generate_embed(status, msg):
    """
    Returns a Discord Embed with color depending on the message's status and custom error message.
    """
    colors = {
        'Error': 0x992d22
    }
    return discord.Embed(title = status, color = colors[status], description = msg)