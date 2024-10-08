import discord
from discord.ext import commands
import random
import asyncio
import os  

intents = discord.Intents.default()
intents.message_content = True 
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)


def generate_code():
    return str(random.randint(10000000, 99999999))


verification_codes = {}
attempts = {}


def create_embed(title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Utilisez ce code pour la vérification.")
    return embed


async def kick_member(member, reason, channel):
    try:
        await member.kick(reason=reason)
        await channel.send(embed=create_embed("Expulsion", f"{member.mention} a été expulsé pour {reason}.", 0xFF0000))
    except discord.Forbidden:
        await channel.send(f"Je n'ai pas la permission d'expulser {member.mention}.")

@bot.event
async def on_member_join(member):
    guild = member.guild
    role_non_verif = discord.utils.get(guild.roles, name="non vérifié")
    role_verif = discord.utils.get(guild.roles, name="vérifié")
    
    if not role_non_verif or not role_verif:
        await member.send("Le serveur n'a pas encore été configuré pour la vérification.")
        return

    await member.add_roles(role_non_verif)

    code = generate_code()
    verification_codes[member.id] = code
    attempts[member.id] = 3  

    try:
        embed = create_embed(
            "Vérification nécessaire",
            f"Bienvenue {member.mention} ! Pour accéder aux autres salons, merci de taper ce code dans le salon de vérification : **{code}**.\n\nTu as 3 essais. Si tu échoues ou que tu n'écris rien dans 5 minutes, tu seras expulsé.",
            0x00FF00
        )
        await member.send(embed=embed)

    except discord.Forbidden:
        await guild.system_channel.send(f"{member.mention}, je ne peux pas t'envoyer de message privé. Merci d'activer les MP.")

    await asyncio.sleep(300)
    if member.id in verification_codes:  
        await kick_member(member, "Temps de vérification écoulé", guild.system_channel)
        del verification_codes[member.id]
        del attempts[member.id]


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "vérification":  
        member = message.author

        if member.id in verification_codes:
            if message.content == verification_codes[member.id]:
                role_non_verif = discord.utils.get(member.guild.roles, name="non vérifié")
                role_verif = discord.utils.get(member.guild.roles, name="vérifié")

                await member.remove_roles(role_non_verif)
                await member.add_roles(role_verif)

                embed = create_embed(
                    "Vérification réussie",
                    f"Félicitations {member.mention} ! Tu es maintenant vérifié(e) et tu as accès à tous les salons.",
                    0x00FF00
                )
                await message.channel.send(embed=embed)

                del verification_codes[member.id]
                del attempts[member.id]

            else:
                attempts[member.id] -= 1
                if attempts[member.id] > 0:
                    embed = create_embed(
                        "Code incorrect",
                        f"Le code est incorrect. Il te reste {attempts[member.id]} essai(s).",
                        0xFF0000
                    )
                    await message.channel.send(embed=embed)
                else:
                    await kick_member(member, "Trop d'erreurs de vérification", message.channel)
                    del verification_codes[member.id]
                    del attempts[member.id]

        await message.delete()  

    await bot.process_commands(message)


@bot.command()
@commands.has_role("admin")  
async def setup(ctx):
    guild = ctx.guild
    role_non_verif = discord.utils.get(guild.roles, name="non vérifié")
    if not role_non_verif:
        role_non_verif = await guild.create_role(name="non vérifié", reason="Rôle de vérification")
    
    role_verif = discord.utils.get(guild.roles, name="vérifié")
    if not role_verif:
        role_verif = await guild.create_role(name="vérifié", reason="Rôle pour les utilisateurs vérifiés")

    
    if not discord.utils.get(guild.text_channels, name="vérification"):
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),  
            role_non_verif: discord.PermissionOverwrite(read_messages=True, send_messages=True), 
            role_verif: discord.PermissionOverwrite(read_messages=False)  
        }
        await guild.create_text_channel("vérification", overwrites=overwrites)

   
    for channel in guild.text_channels:
        if channel.name != "vérification":
            await channel.set_permissions(role_non_verif, read_messages=False) 

    await ctx.send("Le serveur a été configuré avec succès.")


bot.run('VOTRE TOKEN DE BOT')
