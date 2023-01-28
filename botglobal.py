import os
import discord
from discord.ext import commands
from discord import app_commands
import openai
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DiscordIsolationToken")

openai.api_key = os.getenv("OpenAIKey")
guildsWithAI = []

# function to save / read the guildsWithAI list to a file
def saveGuildsWithAI():
    with open("guildsWithAI.txt", "w") as f:
        for guild in guildsWithAI:
            f.write(f"{guild}")

def readGuildsWithAI():
    with open("guildsWithAI.txt", "r") as f:
        for line in f:
            guildsWithAI.append(int(line))

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
    async def syncSlashes(self) -> None:
        await self.tree.sync()
        print("Synced slash commands")
    async def on_ready(self):
        print(f"{self.user} has connected")
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            # only reply if the channel still exists
            if ctx.guild.get_channel(ctx.channel.id) is not None:
                await ctx.reply("You don't have permission to use this command", ephemeral=True)
            return
        if ctx.guild.get_channel(ctx.channel.id) is not None:
            await ctx.reply(error, ephemeral=True)
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.startswith("!") and message.content != "!":
            # won't run command if author is in an isolated channel
            if (message.channel.id in findIsolatedChannels(message.guild) or message.channel.name == "isolated-" + str(message.author.id)) and not message.author.guild_permissions.manage_messages:
                await message.channel.send("You can't use commands in an isolated channel")
                return
            await self.process_commands(message)
            return
        secureChannels = findIsolatedChannels(message.guild)
        if message.guild.get_channel(message.channel.id).name == "general":
            embed = IsolationMessageEmbed(message)
            for cnnl in secureChannels:
                await message.guild.get_channel(cnnl).send(embed=embed)
            return
        if message.channel.id not in secureChannels:
            return # add option to allow messages from other channels
            embed = IsolationMessageEmbed(message)
            for cnnl in secureChannels:
                await message.guild.get_channel(cnnl).send(embed=embed)
        else:
            if message.content.startswith("!"):
                await message.channel.send("You can't use commands in an isolated channel")
                return
            if message.author.guild_permissions.manage_messages:
                return
            readGuildsWithAI()
            if message.guild.id in guildsWithAI:
                response = openai.Completion.create(engine="text-davinci-003", prompt=f"The following is a discord message. Is it appropriate for general audiences (Yes / No)?\n'{message.content}'\n", temperature=0.1, max_tokens=10)
                if "Y" in response.choices[0].text:
                    embed = IsolationMessageEmbed(message, True)
                    generalChannel = findGeneralChannel(message.guild)
                    await message.guild.get_channel(generalChannel).send(embed=embed)
                else:
                    await message.channel.send("Your message has been automatically denied.")
                return
            verificationChannel = findVerificationChannel(message.guild)
            if verificationChannel is None:
                await message.channel.send("There is no verification channel set up for this server")
                return
            embed = IsolationMessageEmbed(message, True)
            await message.guild.get_channel(verificationChannel).send(f"{message.author.name}: {message.content}", view=VerificationMessage(message, embed))

class VerificationMessage(discord.ui.View):
    def __init__(self, message: discord.Message, messageEmbed: discord.Embed):
        super().__init__()
        self.message = message
        self.enabled = True
        self.messageEmbed = messageEmbed
    async def disableAllButtons(self, interaction: discord.Interaction, keepUnblock: False):
        for child in self.children:
            if child.label == "Unblock" and keepUnblock:
                child.disabled = False
            else:
                child.disabled = True
        await interaction.response.edit_message(view=self)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.blurple)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        generalChannel = findGeneralChannel(self.message.guild)
        await self.message.guild.get_channel(generalChannel).send(embed=self.messageEmbed)
        button.style = discord.ButtonStyle.success
        button.label = "Accepted"
        await self.disableAllButtons(interaction, False)
        self.stop()
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.secondary)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.channel.send("Your message has been denied.")
        button.style = discord.ButtonStyle.success
        button.label = "Denied"
        await self.disableAllButtons(interaction, False)
        self.stop()
    @discord.ui.button(label="Block", style=discord.ButtonStyle.danger)
    async def block(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.channel.send("You have been blocked from sending messages")
        await self.message.channel.set_permissions(self.message.author, send_messages=False, read_messages=True)
        button.style = discord.ButtonStyle.success
        button.label = "Blocked"
        await self.disableAllButtons(interaction, True)
    @discord.ui.button(label="Unblock", style=discord.ButtonStyle.secondary, disabled=True)
    async def unblock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.message.channel.set_permissions(self.message.author, read_messages=True)
        await self.message.channel.send("You have been unblocked from sending messages")
        button.style = discord.ButtonStyle.success
        button.label = "Unblocked"
        await self.disableAllButtons(interaction, False)
        self.stop()

class IsolatedInformation(discord.ui.View):
    def __init__(self):
        super().__init__()
    @discord.ui.button(label="Appeal", style=discord.ButtonStyle.blurple)
    async def appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        verificationChannel = findVerificationChannel(interaction.channel.guild)
        if verificationChannel is None:
            await interaction.channel.send("There is no verification channel set up for this server")
            button.style = discord.ButtonStyle.danger
            button.label = "Appeal Failed"
            button.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()
            return
        await interaction.channel.guild.get_channel(verificationChannel).send(f"{interaction.user.mention} has requested an appeal. Their channel is {interaction.channel.mention}")
        button.style = discord.ButtonStyle.success
        button.label = "Appeal Sent"
        button.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

# create an embed with the avatar of the message author and the message content
class IsolationMessageEmbed(discord.Embed):
    def __init__(self, message: discord.Message, isolated = False):
        super().__init__()
        if isolated:
            self.set_author(name="[Isolated] " + message.author.name, icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        else:
            name = message.author.name
            if message.author.guild_permissions.administrator:
                name = "[Admin] " + name
            elif message.author.guild_permissions.manage_messages:
                name = "[Mod] " + name
            self.set_author(name=name, icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        self.description = message.content
        self.timestamp = message.created_at

bot = Bot()

@bot.command(name="sync", description="Sync slash commands")
async def sync(ctx):
    if ctx.author.id != 621395819131568158:
        await ctx.reply("You don't have permission to use this command")
        return
    await bot.syncSlashes()
    await ctx.reply("Synced slash commands")

@bot.command(name="ping", description="Ping the bot")
async def ping(ctx):
    print("received ping")
    await ctx.reply("pong")

def findIsolatedChannels(guild: discord.Guild):
    secureChannels = []
    for channel in guild.channels:
        if channel.name.startswith("isolated-"):
            secureChannels.append(channel.id)
    return secureChannels

def findUsersIsolatedChannel(guild: discord.Guild, user: discord.Member):
    for channel in guild.channels:
        if channel.name == f"isolated-{user.id}":
            return channel.id
    return None

def findVerificationChannel(guild: discord.Guild):
    for channel in guild.channels:
        if channel.name.startswith("verify-isolation"):
            return channel.id
    return None

def findGeneralChannel(guild: discord.Guild):
    for channel in guild.channels:
        if channel.name.startswith("general"):
            return channel.id

@bot.hybrid_command(name="setup", description="Set up the channels, roles, and categories for isolation")
@commands.has_permissions(administrator=True)
async def setup(ctx: commands.Context):
    await ctx.guild.create_text_channel("verify-isolation", overwrites={
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True)})
    await ctx.guild.create_category("Isolated", overwrites={
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True)})
    await ctx.guild.create_role(name="isolated", permissions=discord.Permissions(view_channel=False))
    await ctx.reply("Set up isolation category and verification channel")

# cycle through all channels except isolated ones and remove the view_channel permission for the isolated role
@bot.hybrid_command(name="setup_role", description="Prevent isolated users from viewing channels")
@commands.has_permissions(administrator=True)
async def setupRole(ctx: commands.Context):
    isolatedRole = discord.utils.get(ctx.guild.roles, name="isolated")
    for channel in ctx.guild.channels:
        if channel.name.startswith("isolated-"):
            continue
        await channel.set_permissions(isolatedRole, view_channel=False)
    await ctx.reply("Set up isolated role")

@bot.hybrid_command(name="isolate", description="Select a member to isolate")
@commands.has_permissions(administrator=True)
async def isolateMember(ctx: commands.Context, member: discord.Member):
    isolatedRole = discord.utils.get(ctx.guild.roles, name="isolated")
    await member.add_roles(isolatedRole)
    isolationcategory = discord.utils.get(ctx.guild.categories, name="Isolated")
    await ctx.guild.create_text_channel(f"isolated-{member.id}", category=isolationcategory, overwrites={
        ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.guild.me: discord.PermissionOverwrite(view_channel=True),
        member: discord.PermissionOverwrite(view_channel=True)}, slowmode_delay=15)
    for channel in ctx.guild.channels:
        if channel.name == f"isolated-{member.id}":
            await channel.send(f"{member.mention} You have been isolated. You can see messages, but all messages you send will be verified by a staff member. If you abuse this, you will be blocked from sending messages.\n\nIf you believe this is a mistake, please appeal by clicking the button below.", view=IsolatedInformation())
    await ctx.send("Isolated member")

@bot.hybrid_command(name="unisolate", description="Remove a member from isolation, and delete their channel")
@commands.has_permissions(administrator=True)
async def unisolateMember(ctx: commands.Context, member: discord.Member):
    isolatedRole = discord.utils.get(ctx.guild.roles, name="isolated")
    await member.remove_roles(isolatedRole)
    for channel in ctx.guild.channels:
        if channel.name == f"isolated-{member.id}":
            await channel.delete()
    await ctx.send("Removed member from isolation")

# manually block / unblock a user
@bot.hybrid_command(name="block-isolated", description="Block an isolated user from sending messages")
@commands.has_permissions(administrator=True)
async def blockUser(ctx: commands.Context, member: discord.Member):
    channel = findUsersIsolatedChannel(ctx.guild, member)
    if channel is None:
        await ctx.send("User is not isolated", ephemeral=True)
        return
    await ctx.guild.get_channel(channel).set_permissions(member, send_messages=False, read_messages=True)
    await ctx.guild.get_channel(channel).send(f"{member.mention} You have been blocked from sending messages")
    await ctx.send("Blocked user")

@bot.hybrid_command(name="unblock-isolated", description="Unblock an isolated user from sending messages")
@commands.has_permissions(administrator=True)
async def unblockUser(ctx: commands.Context, member: discord.Member):
    channel = findUsersIsolatedChannel(ctx.guild, member)
    if channel is None:
        await ctx.send("User is not isolated", ephemeral=True)
        return
    await ctx.guild.get_channel(channel).set_permissions(member, read_messages=True)
    await ctx.guild.get_channel(channel).send(f"{member.mention} You have been unblocked from sending messages")
    await ctx.send("Unblocked user")

# lock down all isolated channels
@bot.hybrid_command(name="lockdown-isolated", description="Lock down all isolated channels")
@commands.has_permissions(administrator=True)
async def lockdownIsolated(ctx: commands.Context):
    failedChannels = 0
    for channel in ctx.guild.channels:
        if channel.name.startswith("isolated-"):
            try:
                isolatedRole = discord.utils.get(ctx.guild.roles, name="isolated")
                await channel.set_permissions(isolatedRole, send_messages=False, read_messages=True)
            except:
                failedChannels += 1
    if failedChannels > 0:
        await ctx.send(f"Attempted to lock down isolated channels, but {failedChannels} channel{'s' if failedChannels > 1 else ''} failed to lock down")
        return
    await ctx.send("Locked down all isolated channels")

# enable / disable ai for a guild
@bot.hybrid_command(name="enable-ai", description="Enable AI for this server")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.guild.id)
@commands.has_permissions(administrator=True)
async def enableAI(ctx: commands.Context):
    readGuildsWithAI()
    if ctx.guild.id in guildsWithAI:
        await ctx.send("AI is already enabled", ephemeral=True)
        return
    guildsWithAI.append(ctx.guild.id)
    saveGuildsWithAI()
    await ctx.send("Enabled AI", ephemeral=True)

@bot.hybrid_command(name="disable-ai", description="Disable AI for this server")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.guild.id)
@commands.has_permissions(administrator=True)
async def disableAI(ctx: commands.Context):
    readGuildsWithAI()
    if ctx.guild.id not in guildsWithAI:
        await ctx.send("AI is already disabled", ephemeral=True)
        return
    guildsWithAI.remove(ctx.guild.id)
    saveGuildsWithAI()
    await ctx.send("Disabled AI", ephemeral=True)


bot.run(TOKEN)