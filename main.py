# 提醒：要記得填入ＭｙＳＱＬ的密碼
# 提醒：要記得填入bot token

# 官方的函式庫
import asyncio
import dataframe_image as dfi
from datetime import timedelta
import datetime
import discord
from discord import app_commands
from discord.ext import tasks
from discord import ui
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import mysql.connector
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import random
from time import sleep
from typing import Optional
from win32com import client as ci


# 自己的函式
import period_function  # 與period deadline有關的function全部放在這邊 # 需額外安裝 python-dateutil 函式庫


# 還沒做的事情：
# 提醒使用者 都要使用半形
# 甘特圖沒有控制 guild、matlibplot 中文

# mysql的設定
db = mysql.connector.connect(
    host='localhost',
    user='root',
    passwd='',  # 自己填入資料庫密碼
    database=''
)
mycursor = db.cursor(buffered=True)
# mysql的設定結束

plt.rcParams['font.sans-serif'] = ['Taipei Sans TC Beta']

# discord的設定
# # 要記得在discord portal的Bot將PRESENCE INTENT、SERVER MEMBERS INTENT、MESSAGE CONTENT INTENT給打開
TOKEN = ''  # 自己填入TOKEN


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()


intents = discord.Intents.default()
intents.members = True
intents.presences = True
client = MyClient(intents=intents)
# discord的設定結束


# 放入toNotify
def InsertToNotify(dest: datetime, deadlineID: int):
    # """放入到toNotify表格"""
    now = datetime.datetime.now()
    sql = "INSERT INTO `toNotify` (`deadlineID`, `Ndatetime`, `num`) VALUES (%s, %s, %s)"
    result = dest-now
    datetimeAndNum = [(0, 1), (3, 2), (1, 3), (6, 4), (24, 5)]

    end = 0

    if (result.days >= 1):  # 目前時間離deadline截止時間還有超過一天
        end = len(datetimeAndNum)
    elif (result.seconds > 21600):  # 目前時間離deadline截止時間還有超過6小時
        end = len(datetimeAndNum) - 1
    elif (result.seconds > 3600):  # 目前時間離deadline截止時間還有超過1小時
        end = len(datetimeAndNum) - 2
    elif (result.seconds > 180):  # 目前時間離deadline截止時間還有超過3分鐘
        end = len(datetimeAndNum) - 3
    else:
        end = len(datetimeAndNum) - 2

    for info in range(end):
        if (datetimeAndNum[info][1] < 3):
            val = (deadlineID, dest - datetime.timedelta(
                seconds=datetimeAndNum[info][0]*60), datetimeAndNum[info][1])
        else:
            val = (deadlineID, dest - datetime.timedelta(
                hours=datetimeAndNum[info][0]), datetimeAndNum[info][1])

        mycursor.execute(sql, val)
        db.commit()

    # """放入到toNotify表格"""
# 放入toNotify結束


# 放入userdeadline
def InsertToUserdeadline(deadlineID: int, member: str):
    now = datetime.datetime.now()
    sql = "INSERT INTO `userdeadline` (`deadlineID`, `discordID`, `status`, `start_time`) VALUES (%s, %s, %s, %s)"
    member = member.strip("<>@")
    val = (deadlineID, member, 0, now)
    mycursor.execute(sql, val)
    db.commit()
    return member
# 放入userdeadline結束


def choiceLList(start, end):
    """包含end的數字"""
    choiceList = []
    for i in range(start, end+1):
        choiceList.append(discord.app_commands.Choice(name=i, value=i))
    return choiceList


@tasks.loop(seconds=1)
async def task():
    now = datetime.datetime.now()
    sql = "SELECT * from toNotify WHERE Ndatetime BETWEEN %s and %s ORDER BY Ndatetime"
    val = (now, now + datetime.timedelta(seconds=1))
    mycursor.execute(sql, val)

    toNotify = []  # 裝接下來要訊息發送的toNotify表格裡的資料
    msg = []  # 裝接下來要發送的文字訊息

    for info in mycursor:
        toNotify.append(info)

    sql = "DELETE from toNotify WHERE Ndatetime < %s"  # 將Notify中已經過期的資料給刪除掉
    val = (now + datetime.timedelta(seconds=0.5), )
    mycursor.execute(sql, val)
    db.commit()

    remindmsg = ["", "is overdue\n🔥🔥🔥🔥🔥", "is about to due in 3 minutes\n🔥🔥🔥",
                 "is about to due in 1 hour\n🔥", "is about to due in 6 hours", "is about to due in 24 hours"]

    for x in toNotify:  # 先找出與toNotify的deadlineID相符合的userdeadline資料
        deadlineID = x[0]
        allMen = []
        unfinishMem = []
        sql = "SELECT discordID, status from userdeadline WHERE deadlineID=%s ORDER BY discordID"
        val = (deadlineID, )
        mycursor.execute(sql, val)
        for member in mycursor:  # 在userdeadline表格中，將要提醒的使用者資料加入到unfinishMem中
            allMen.append(member[0])
            if (member[1] == 0):
                unfinishMem.append(client.get_user(int(member[0])).mention)

        sql = "SELECT channel, PN, periodID, deadlineName, guild, channel, status from deadline WHERE deadlineID=%s"
        val = (deadlineID, )
        mycursor.execute(sql, val)
        # 進到deadline表格，並存取要傳出的訊息、頻道、PN、periodID、deadline名稱、伺服器以及頻道
        for deadline in mycursor:
            if (len(unfinishMem) != 0):  # 如果有成員尚未完成
                msg.append(
                    [f'Hey! {" ".join(unfinishMem)}\n{deadline[3]} {remindmsg[x[2]]}\n----------------', deadline[0], deadline[1], deadline[2], deadline[3], deadline[4], deadline[5]])
            elif (deadline[6] == 1):  # 如果成員都已經完成
                msg.append(
                    [f'Looks like everyone has finish the mission--{deadline[3]}, good job!\n----------------', deadline[0], deadline[1], deadline[2], deadline[3], deadline[4], deadline[5]])

        if (x[2] == 1):  # 如果是最後一次提醒
            # Period deadline需先將下期的資料重新創制並放入deadline中(代表deadline中會保存每一期的period deadline資料)，接著再重新創制userdeadline，最後再放入toNotify中
            if (msg[-1][2] == "P"):

                # 先找到該筆period deadline的週期以及下一期的時間
                sql = "SELECT frequency, day, time From periodDeadline WHERE periodID=%s"
                val = (msg[-1][3], )
                mycursor.execute(sql, val)
                for xx in mycursor:
                    ExactDate = period_function.GetExactDate(datetime.datetime.now(
                    ) + datetime.timedelta(seconds=5), xx[0], xx[1], str(xx[2]))
                msg[-1].append(ExactDate)

                # 將period_deadline存進deadline
                sql = "INSERT INTO `deadline` (`periodID`, `deadlineName`, `PN`, `datetime`, `status`, `guild`, `channel`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                val = (msg[-1][3], msg[-1][4], msg[-1][2],
                       ExactDate, '0', msg[-1][5], msg[-1][6])
                mycursor.execute(sql, val)
                db.commit()

                # 將該deadline的ID取出
                deadlineID = mycursor.lastrowid

                # """放入到toNotify表格"""
                InsertToNotify(dest=ExactDate, deadlineID=deadlineID)
                # """放入到toNotify表格"""

                # 放入userdeadline
                for x in range(len(allMen)):
                    InsertToUserdeadline(
                        deadlineID=deadlineID, member=allMen[x])
                    allMen[x] = client.get_user(int(allMen[x])).mention
                allMen = " ".join(allMen)
                # 放入userdeadline結束

                msg[-1].append(allMen)

    for x in msg:
        await client.get_channel(int(x[1])).send(x[0])
        if (x[2] == 'P' and "is overdue\n🔥🔥🔥🔥🔥" in x[0]):
            await client.get_channel(int(x[6])).send(f'Mission: {x[4]}\nDeadline(period): {str(x[7])[0:19]}\nMember: {x[8]}\n----------------')


# 登錄提醒
@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    task.start()


# 替換掉/start的東西
@client.event
async def on_guild_join(guild: discord.Guild):
    sql = "INSERT IGNORE INTO `user` (`name`, `discordID`, `guild`) VALUES (%s, %s, %s)"
    for member in guild.members:
        if (member.bot == 1):
            continue
        val = (member.display_name, member.id, guild.id)
        mycursor.execute(sql, val)
        db.commit()

    embed = discord.Embed(title="Deadline Manager 使用介紹",
                          description="以下為bot所有的指令: (尚不支援身分組相關功能)", color=0xeb8d67)

    embed.add_field(name="/set_deadline",
                    value="設定普通的deadline\n_", inline=True)
    embed.add_field(name="/set_period_deadline",
                    value="設定週期式deadline\n_", inline=True)
    embed.add_field(name="/my_deadline",
                    value="查看自己尚未完成的deadline(僅自己可見)\n_", inline=True)
    embed.add_field(name="/deadline_cancel",
                    value="刪除所選的deadline，不保留deadline資料\n_", inline=True)
    embed.add_field(name="/period_cancel",
                    value="刪除所選的週期，但仍保留以往的deadline資料\n_", inline=True)
    embed.add_field(
        name="/check", value="查看伺服器歷史以來的所有deadline狀態\n_", inline=True)
    embed.add_field(name="/mission_complete",
                    value="完成deadline時呼叫，系統會記錄繳交時間及日期\n_", inline=True)
    embed.add_field(name="/suggestion_to",
                    value="組內互評表，可選擇是否當下將互評表印出\n_", inline=True)
    embed.add_field(name="/whos_freerider",
                    value="印出分工成果表(含表格及甘特圖)", inline=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False),
        guild.me: discord.PermissionOverwrite(send_messages=True)
    }

    # category = await guild.create_category(name="Deadline Manager", reason="為了讓你知道如何使用Deadline Manager")

    channel = await guild.create_text_channel(name="使用守則", overwrites=overwrites, category=None, position=0)

    await channel.send(embed=embed)
    await channel.send("⚠️目前Deadline Manager尚不支援有關任何身分組的操作 比如: @某身分組\nDeadline Manager does not support any function with Roles, for example @roles")
    await channel.send("⚠️若要讓/whos_freerider的圖表發揮最顯著的效果，建議deadline時長須超過一周\nmake sure your deadline time lengh exceed 1 week to ensure the deadline appear on the Gantt chart")
    # await channel.send("For more information, please check out on our website: ")

# 機器人被踢出後會自動刪除一切相關的東西


@client.event
async def on_guild_remove(guild: discord.Guild):
    sql = "DELETE FROM suggestion WHERE guild=%s"
    val = (guild.id, )
    mycursor.execute(sql, val)
    db.commit()

    sql = "DELETE FROM user WHERE guild=%s"
    val = (guild.id, )
    mycursor.execute(sql, val)
    db.commit()

    sql = "SELECT periodID FROM deadline WHERE guild=%s"
    val = (guild.id, )
    mycursor.execute(sql, val)
    deleteList = []
    for periodID in mycursor:
        deleteList.append(periodID[0])

    for periodID in deleteList:
        sql = "DELETE FROM periodDeadline WHERE periodID=%s"
        val = (periodID, )
        mycursor.execute(sql, val)
        db.commit()

    sql = "DELETE FROM deadline WHERE guild=%s"
    val = (guild.id, )
    mycursor.execute(sql, val)
    db.commit()

# 新成員加入時會insert資料


@client.event
async def on_member_join(member: discord.Member):
    sql = "INSERT IGNORE INTO `user` (`name`, `discordID`, `guild`) VALUES (%s, %s, %s)"
    val = (member.display_name, member.id, member.guild.id)
    mycursor.execute(sql, val)
    db.commit()

# 成員離開後會delete其資料


@client.event
async def on_member_remove(member: discord.Member):
    sql = "DELETE FROM user WHERE discordID=%s and guild=%s"
    val = (member.id, member.guild.id)
    mycursor.execute(sql, val)
    db.commit()

# 成員更新名稱時


@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    sql = "UPDATE user SET name=%s WHERE discordID=%s AND guild=%s"
    val = (after.display_name, after.id, after.guild.id)
    mycursor.execute(sql, val)
    db.commit()


# 功能: /deadline_cancel
@client.tree.command()
@app_commands.describe(
    deadline='Please select from the deadline option. N for normal deadline, P for period deadline',
)
async def deadline_cancel(interaction: discord.Interaction, deadline: int):
    '''我們會將該Deadline完整刪除掉'''
    deadlineID = deadline
    if (deadlineID == 0):
        await interaction.response.send_message("You have nothing to delete😠")
        return

    sql = "SELECT deadlineName, datetime, PN, periodID from deadline WHERE deadlineID=%s"  # 將要發送的內容先拿下來
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()
    for Info in mycursor:
        deadlineInfo = Info

    theLatest = 0
    if (deadlineInfo[2] == "P"):
        sql = "SELECT deadlineID from deadline where periodID=%s ORDER BY datetime desc limit 1"
        val = (deadlineInfo[3], )
        mycursor.execute(sql, val)
        for ID in mycursor:
            if (ID[0] == deadlineID):
                theLatest = 1

    sql = "SELECT discordID from userdeadline WHERE deadlineID=%s"  # 將要@的成員先拿下來
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()
    memberList = []
    memberIDList = []
    for member in mycursor:
        memberIDList.append(member[0])
        memberList.append(client.get_user(int(member[0])).mention)

    sql = "DELETE from deadline WHERE deadlineID=%s"  # 將deadline資料給刪除掉
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()

    await interaction.response.send_message(f'{" ".join(memberList)}\n{interaction.user.display_name} has deleted the mission: {deadlineInfo[0]}, which due in {str(deadlineInfo[1])[0:19]}')

    if (theLatest == 1):

        # 先找到該筆period deadline的週期以及下一期的時間
        sql = "SELECT frequency, day, time From periodDeadline WHERE periodID=%s"
        val = (deadlineInfo[3], )
        mycursor.execute(sql, val)
        for xx in mycursor:
            time = xx[2]
            ExactDate = period_function.GetExactDate(
                deadlineInfo[1], xx[0], xx[1], str(xx[2]))

        # 將period_deadline存進deadline
        sql = "INSERT INTO `deadline` (`periodID`, `deadlineName`, `PN`, `datetime`, `status`, `guild`, `channel`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (deadlineInfo[3], deadlineInfo[0], deadlineInfo[2],
               ExactDate, '0', interaction.guild_id, interaction.channel_id)
        mycursor.execute(sql, val)
        db.commit()

        # 將該deadline的ID取出
        deadlineID = mycursor.lastrowid

        # """放入到toNotify表格"""
        InsertToNotify(dest=ExactDate, deadlineID=deadlineID)
        # """放入到toNotify表格"""

        # 放入userdeadline
        for member in memberIDList:
            InsertToUserdeadline(deadlineID=deadlineID, member=member)
        # 放入userdeadline結束

        await interaction.channel.send(f'--------------------------------------\nMission: {deadlineInfo[0]}\nDeadline(period): {ExactDate.date()} {time}\nMember: {" ".join(memberList)}\n--------------------------------------')


@deadline_cancel.autocomplete('deadline')
async def deadline_cancel_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:

    sql = "SELECT deadlineID, deadlineName, datetime, PN FROM deadline WHERE guild=%s ORDER BY datetime"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    choiceList = []

    for deadlineID in mycursor:
        name = f'(Due: {str(deadlineID[2])[0:19]}) ({deadlineID[3]}) Deadline Name: {deadlineID[1]}'
        choiceList.append(app_commands.Choice(name=name, value=deadlineID[0]))

    if (len(choiceList) != 0):
        return choiceList
    else:
        choiceList.append(app_commands.Choice(name="you have nothing to delete :(",
                                              value=0))
        return choiceList


# 功能: /period_cancel
@client.tree.command()
@app_commands.describe(
    period='Please select from the period option',
)
async def period_cancel(interaction: discord.Interaction, period: int):
    '''刪除period，但會保留以往的紀錄，仍會進行最後一次的period deadline提醒'''
    periodID = period
    if (periodID == 0):
        await interaction.response.send_message("You have nothing to delete😠")
        return

    sql = "SELECT frequency, day, time from periodDeadline WHERE periodID=%s"  # 將要發送的內容先拿下來
    val = (periodID, )
    mycursor.execute(sql, val)
    db.commit()
    for info in mycursor:
        frequency = info[0]
        day = info[1]
        time = info[2]

    sql = "SELECT deadlineName, deadlineID from deadline WHERE periodID=%s ORDER BY datetime DESC LIMIT 1"  # 將要發送的內容先拿下來
    val = (periodID, )
    mycursor.execute(sql, val)
    db.commit()
    for info in mycursor:
        deadlineName = info[0]
        deadlineID = info[1]

    sql = "SELECT discordID from userdeadline WHERE deadlineID=%s"  # 將要@的成員先拿下來
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()
    memberList = []
    for member in mycursor:
        memberList.append(client.get_user(int(member[0])).mention)

    sql = "UPDATE deadline SET PN=%s WHERE periodID=%s"  # 將deadline資料給刪除掉
    val = ('N', periodID)
    mycursor.execute(sql, val)
    db.commit()

    sql = "DELETE from periodDeadline WHERE periodID=%s"
    val = (periodID, )
    mycursor.execute(sql, val)
    db.commit()

    await interaction.response.send_message(f'{" ".join(memberList)}\n{interaction.user.display_name} has deleted the period: {deadlineName}, for its period is {frequency}_{day} time is {time}')


@period_cancel.autocomplete('period')
async def period_cancel_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:

    sql = "SELECT periodDeadline.periodID, deadline.deadlineName, periodDeadline.frequency, periodDeadline.day, periodDeadline.time FROM periodDeadline, deadline WHERE deadline.guild=%s AND deadline.periodID=periodDeadline.periodID ORDER BY periodDeadline.periodID"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    choiceList = []
    last_id = 0

    for periodID in mycursor:
        if (last_id != periodID[0]):
            name = f'period: {periodID[2]}_{periodID[3]} time: {periodID[4]} period_deadline_name: {periodID[1]}'
            choiceList.append(app_commands.Choice(
                name=name, value=periodID[0]))
        last_id = periodID[0]

    if (len(choiceList) != 0):
        return choiceList
    else:
        choiceList.append(app_commands.Choice(name="you have nothing to delete :(",
                                              value=0))
        return choiceList


# 功能: /set_deadline
@client.tree.command(description="設定普通的deadline")
@app_commands.describe(
    date='yyyy-mm-dd',
    time='hh:mm (請用半形)',
    mission_name='what is your deadline about? (describe spicificly)',
    member_or_members='@someone @someone @someone (it\'s fine if there\'s only one member include in this mission)',
)
async def set_deadline(interaction: discord.Interaction, date: str, time: str, mission_name: str, member_or_members: str):
    # 防呆機制
    failmsg = []
    if (date.count("-") != 2):
        failmsg.append("wrong date format. (correct example: 2023-02-04)")
    if (int(date.split("-")[1]) < 1 or int(date.split("-")[1]) > 12):
        failmsg.append("wrong month")
    if (period_function.TheDateDoesNotExist(date.split("-")[0], date.split("-")[1], date.split("-")[2])):
        failmsg.append("wrong date")
    if ("：" in time):
        time = ":".join(time.split("："))
    if (time.count(":") != 1):
        failmsg.append("wrong time format. (correct example: 00:33)")
    else:
        if (int(time.split(":")[0]) < 0 or int(time.split(":")[0]) > 23):
            failmsg.append("wrong hour")
        if (int(time.split(":")[1]) < 0 or int(time.split(":")[1]) > 59):
            failmsg.append("wrong minute")
    member_or_members = member_or_members.split()

    if ("@everyone" in member_or_members):
        for member in client.get_guild(interaction.guild.id).members:
            if (member.bot == 1):
                continue
            member_or_members.append(member.mention)
        member_or_members.pop(0)

    if ("@here" in member_or_members):
        for member in client.get_guild(interaction.guild.id).members:
            if (member.bot == 1 or member.raw_status != "online" or member in member_or_members):
                continue
            member_or_members.append(member.mention)
        member_or_members.pop(0)

    for x in member_or_members:
        if (("<" not in x) or ("@" not in x) or (">" not in x)):
            failmsg.append(
                "wrong member format, you just need to @someone")
            break

    # 這邊是為了將機器人排除掉
    byebyeList = []
    for x in range(len(member_or_members)):
        if (client.get_user(int(member_or_members[x].strip("<@>"))).bot == 1):
            byebyeList.append(x)

    for x in byebyeList:
        member_or_members.pop(x)
        for y in range(len(byebyeList)):
            byebyeList[y] -= 1
            # 這邊是為了將機器人排除掉

    if (len(member_or_members) == 0):
        failmsg.append("Please don\'t add bot in your deadline")

    if (len(failmsg) != 0):
        await interaction.response.send_message("\n".join(failmsg))
        return
    # 防呆機制結束

    dtime = str(date) + " " + str(time)

    # 設定Deadline
    # 將deadline存進deadline的table
    sql = "INSERT INTO `deadline` (`deadlineName`, `PN`, `datetime`, `status`, `guild`, `channel`) VALUES (%s, %s, %s, %s, %s, %s)"
    val = (mission_name, 'N', dtime, '0',
           interaction.guild_id, interaction.channel_id)
    mycursor.execute(sql, val)
    db.commit()
    # 將deadline存進deadline的table結束

    deadlineID = mycursor.lastrowid  # 將該deadline的ID取出

    # 放入到toNotify表格
    dest = datetime.datetime(int(date.split("-")[0]), int(date.split("-")[1]), int(
        date.split("-")[2]), int(time.split(":")[0]), int(time.split(":")[1]), 0, 0)
    InsertToNotify(dest=dest, deadlineID=deadlineID)
    # 放入到toNotify表格結束

    # 該deadline放入userdeadline
    for x in range(len(member_or_members)):
        member_or_members[x] = InsertToUserdeadline(deadlineID=deadlineID,
                                                    member=member_or_members[x])
        member_or_members[x] = client.get_user(
            int(member_or_members[x])).mention
    member_or_members = " ".join(member_or_members)
    # 該deadline放入userdeadline結束

    now = datetime.datetime.now()

    if (dest < now):
        await interaction.response.send_message(f'⚠️You have enter a past date for deadline\nMission: {mission_name}\nDeadline: {date} {time}\nMember: {member_or_members}')
        return
    else:
        await interaction.response.send_message(f'Mission: {mission_name}\nDeadline: {date} {time}\nMember: {member_or_members}')


# 功能: /set_period_deadline
@client.tree.command()
@app_commands.describe(
    period='everyDay(remind everyday)/ everyWeek(remind once a week)/ everyMonth(remind once a month)',
    period_day='everyDay: enter 0/ everyWeek: choose from 1 to 7/ everyMonth: choose from 1 to 31',
    time='hh:mm (請用半形)',
    mission_name='what is your deadline about? (describe spicificly)',
    member_or_members='@someone @someone @someone (it\'s fine if there\'s only one member in this mission',
)
@app_commands.choices(period=[
    discord.app_commands.Choice(name='everyDay', value='everyDay'),
    discord.app_commands.Choice(name='everyWeek', value='everyWeek'),
    discord.app_commands.Choice(name='everyMonth', value='everyMonth'),
])
async def set_period_deadline(interaction: discord.Interaction, period: discord.app_commands.Choice[str], period_day: int, time: str, mission_name: str, member_or_members: str):
    """設定週期型的Deadline"""

    # 防呆機制
    failmsg = []
    if (period == "everyDay" and period_day != 0):
        failmsg.append(
            "wrong period_day, please enter 0 in period_day if you want to be remined everyday")
    elif (period == "everyWeek" and (period_day < 1 or period_day > 7)):
        failmsg.append(
            "wrong period_day, please enter a number between 1 to 7 in period_day if you want to be remined everyweek\n(1 for Monday, 2 for Tuesday...etc.)")
    elif (period == "everyWeek" and (period_day < 1 or period_day > 31)):
        failmsg.append("wrong period_day, please enter a number between 1 to 31 in period_day if you want to be remined everymonth\n(if the date you choose doesn\'t exist in the month, we're remind you in that month\'s last day)")

    if ("：" in time):
        time = ":".join(time.split("："))
    if (time.count(":") != 1):
        failmsg.append("wrong time format. (correct example: 00:33)")
    else:
        if (int(time.split(":")[0]) < 0 or int(time.split(":")[0]) > 23):
            failmsg.append("wrong hour")
        if (int(time.split(":")[1]) < 0 or int(time.split(":")[1]) > 59):
            failmsg.append("wrong minute")

    member_or_members = member_or_members.split()
    if (member_or_members[0] == "@everyone"):
        for member in client.get_guild(interaction.guild.id).members:
            if (member.bot == 1):
                continue
            member_or_members.append(member.mention)
        member_or_members.pop(0)

    if ("@here" in member_or_members):
        for member in client.get_guild(interaction.guild.id).members:
            if (member.bot == 1 or member.raw_status != "online" or member in member_or_members):
                continue
            member_or_members.append(member.mention)
        member_or_members.pop(0)

    for x in member_or_members:
        if (("<" not in x) and ("@" not in x) and (">" not in x)):
            failmsg.append(
                "wrong member format, you just need to enter @someone, and don't forget to put a space between each members")
            break

    # 這邊是為了將機器人排除掉
    byebyeList = []
    for x in range(len(member_or_members)):
        if (client.get_user(int(member_or_members[x].strip("<@>"))).bot == 1):
            byebyeList.append(x)

    for x in byebyeList:
        member_or_members.pop(x)
        for y in range(len(byebyeList)):
            byebyeList[y] -= 1
            # 這邊是為了將機器人排除掉

    if (len(member_or_members) == 0):
        failmsg.append("Please don\'t add bot in your deadline")

    if (len(failmsg) != 0):
        await interaction.response.send_message("\n".join(failmsg))
        return
    # 防呆機制結束

    # 將period_deadline的週期資訊存入periodDeadline
    sql = "INSERT INTO `periodDeadline` (`frequency`, `day`, `time`) VALUES (%s, %s, %s)"
    val = (str(period.name), period_day, time)
    mycursor.execute(sql, val)
    db.commit()
    # 將period_deadline的週期資訊存入periodDeadline結束

    # 將該period deadline的ID取出
    periodID = mycursor.lastrowid

    # 將period_deadline存進deadline
    sql = "INSERT INTO `deadline` (`periodID`, `deadlineName`, `PN`, `datetime`, `status`, `guild`, `channel`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    date = period_function.GetExactDate(
        datetime.datetime.now(), str(period.name), period_day, time)
    val = (periodID, mission_name, 'P', date, '0',
           interaction.guild_id, interaction.channel_id)
    mycursor.execute(sql, val)
    db.commit()

    # 將該deadline的ID取出
    deadlineID = mycursor.lastrowid

    # """放入到toNotify表格"""
    dest = datetime.datetime(int(date.year), int(date.month), int(
        date.day), int(time.split(":")[0]), int(time.split(":")[1]), 0, 0)
    InsertToNotify(dest=dest, deadlineID=deadlineID)
    # """放入到toNotify表格"""

    # 放入userdeadline
    for x in range(len(member_or_members)):
        member_or_members[x] = InsertToUserdeadline(deadlineID=deadlineID,
                                                    member=member_or_members[x])
        member_or_members[x] = client.get_user(
            int(member_or_members[x])).mention
    member_or_members = " ".join(member_or_members)
    # 放入userdeadline結束

    await interaction.response.send_message(f'Mission: {mission_name}\nDeadline(period): {date.date()} {time}\nMember: {member_or_members}')


# /my_deadline
@client.tree.command()
@app_commands.describe(show_all='click yes to show all deadline(incluing from other guild), else click no')
@app_commands.choices(show_all=[
    discord.app_commands.Choice(name='yes', value=1),
    discord.app_commands.Choice(name='no', value=0),
])
async def mydeadline(interaction: discord.Interaction, show_all: discord.app_commands.Choice[int]):
    """查看你尚未完成的Deadline，只會顯示給你看"""
    member = interaction.user.id
    if (show_all.value == 1):  # 顯示所有deadline
        sql = "SELECT deadline.PN, deadline.deadlineName, deadline.datetime, deadline.guild FROM deadline, userdeadline WHERE userdeadline.discordID=%s and deadline.deadlineID=userdeadline.deadlineID and userdeadline.status=0 ORDER BY deadline.datetime"
        val = (member, )
    else:
        sql = "SELECT deadline.PN, deadline.deadlineName, deadline.datetime, deadline.guild FROM deadline, userdeadline WHERE userdeadline.discordID=%s and deadline.deadlineID=userdeadline.deadlineID and userdeadline.status=0 and deadline.guild=%s ORDER BY deadline.datetime"
        val = (member, interaction.guild_id)

    mycursor.execute(sql, val)
    msg = "Good to see you " + str(interaction.guild.get_member(int(member)).display_name) + \
        " :)\nThis is your deadline\n--------------------------------------\n"

    now = datetime.datetime.now()

    for x in mycursor:

        if (x[2] < now):
            msg += "\t⚠️This mission is overdue\n"

        if (x[0] == 'N'):
            if (show_all.value == 1):
                msg += "\tMission: " + \
                    str(x[1]) + " (Normal) (From " + \
                    str(client.get_guild(int(x[3])).name) + ")\n"
            else:
                msg += "\tMission: " + str(x[1]) + " (Normal)\n"
        else:
            if (show_all.value == 1):
                msg += "\tMission: " + \
                    str(x[1]) + " (Period) (From " + \
                    str(client.get_guild(int(x[3])).name) + ")\n"
            else:
                msg += "\tMission: " + str(x[1]) + " (Period)\n"

        msg += "\tDue: " + str(x[2]) + \
            "\n--------------------------------------\n"

    if (msg == "Good to see you " + str(interaction.guild.get_member(int(member)).display_name) + " :)\nThis is your deadline\n--------------------------------------\n"):
        msg = "Good to see you " + \
            str(interaction.guild.get_member(int(member)).display_name) + \
            " :)\nYou have no deadline now, "
        list = ("go water your plant!", "go feed your cat!", "go find yourself something to do!", "just relax!", "go eat something!",
                "go play jigsaw puzzle!", "go out to the great outdoors!", "go play fetch with your dog!", "go make your mama some cookies!")
        msg += list[random.randrange(len(list))]

    await interaction.response.send_message(content=msg, ephemeral=True)


# /check
@client.tree.command(description="查看所有deadline的狀態")
async def check(interaction: discord.Interaction):
    Fullmsg = ["Those are the deadline from " +
               interaction.guild.name + "\n--------------------------------------\n", ]

    jokelist = ("", "", "", ", Good Job!  Nobody:3", "", "", "", "", "")

    guildDeadline = []
    sql = "SELECT deadlineID, deadlineName, PN, datetime, status FROM deadline WHERE guild=%s ORDER BY datetime"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    for x in mycursor:
        guildDeadline.append(x)

    for x in guildDeadline:
        msg = ""
        if (x[3] < datetime.datetime.now()):
            msg += "\t⚠️This mission is overdue\n"

        if (x[2] == 'N'):
            msg += "\tMission: " + \
                str(x[1]) + " (Normal)\n" + "\tDue: " + str(x[3]) + "\n"
        else:
            msg += "\tMission: " + \
                str(x[1]) + " (Period)\n" + "\tDue: " + str(x[3]) + "\n"

        sql = "SELECT discordID, status FROM userdeadline WHERE deadlineID=%s ORDER BY status, discordID"
        val = (x[0], )
        mycursor.execute(sql, val)

        if (x[4] == 0):
            finish = []
            unfinish = []
            for xx in mycursor:
                if (xx[1] == 0):
                    unfinish.append(client.get_user(int(xx[0])).mention)
                else:
                    finish.append(interaction.guild.get_member(
                        int(xx[0])).display_name)

            if (len(finish) == 0):
                msg += "\tNobody has finish this deadline" + \
                    jokelist[random.randrange(
                        len(jokelist))] + "\n--------------------------------------\n"
            else:
                msg += "\tUnfinish members: " + " ".join(unfinish) + "\n"
                msg += "\tFinish members: " + \
                    " ".join(finish) + \
                    "\n--------------------------------------\n"
        else:
            msg += "\tMission has been successfully completed 😎" + \
                "\n--------------------------------------\n"
        Fullmsg.append(msg)

    if (len(Fullmsg) == 1):
        Fullmsg[0] = "There are no deadlines in " + \
            interaction.guild.name + ", looks like it's time to create a new mission!"

    await interaction.response.send_message(f'Good to see you {interaction.user.display_name} :)')

    for x in range(len(Fullmsg)):
        await interaction.channel.send(content=Fullmsg[x])


# /mission_complete
@client.tree.command()
@app_commands.describe(
    deadline='Please select from the deadline option',  # 這邊可能會有bug 因為deadline的選項只有25個
)
async def mission_complete(interaction: discord.Interaction, deadline: int):
    '''完成任務'''
    deadlineID = deadline
    if (deadlineID == 0):
        await interaction.response.send_message("You have nothing to complete😠")
        return

    sql = "SELECT datetime FROM deadline WHERE deadlineID=%s"
    val = (deadlineID, )
    mycursor.execute(sql, val)
    for x in mycursor:
        Ddatetime = x[0]

    if (Ddatetime < datetime.datetime.now()):
        sql = "UPDATE userdeadline SET status=2, end_time=%s WHERE deadlineID=%s and discordID=%s"
    else:
        sql = "UPDATE userdeadline SET status=1, end_time=%s WHERE deadlineID=%s and discordID=%s"
    val = (datetime.datetime.now(), deadlineID, interaction.user.id)
    mycursor.execute(sql, val)
    db.commit()

    sql = "SELECT userdeadline.status, deadline.deadlineName FROM userdeadline, deadline WHERE deadline.deadlineID=%s and deadline.deadlineID=userdeadline.deadlineID"
    val = (deadlineID, )
    mycursor.execute(sql, val)
    for x in mycursor:
        if (int(x[0]) == 0):
            await interaction.response.send_message(f'Congratulation!! The Mission {x[1]} for {interaction.user.mention} has completed')
            return
        missionName = x[1]

    sql = "UPDATE deadline SET status=1 WHERE deadlineID = %s"
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()

    sql = "DELETE from toNotify WHERE deadlineID=%s and num!=1"  # 將Notify中多餘的提醒資料給刪除掉
    val = (deadlineID, )
    mycursor.execute(sql, val)
    db.commit()

    await interaction.response.send_message(f'Congratulation!! All of the members in {missionName} have finish this mission🥳🥳🥳')


@mission_complete.autocomplete('deadline')
async def mission_complete_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:

    sql = "SELECT deadline.deadlineID, deadline.deadlineName, deadline.datetime FROM deadline, userdeadline WHERE deadline.guild=%s AND userdeadline.discordID=%s AND userdeadline.status=0 AND userdeadline.deadlineID=deadline.deadlineID ORDER BY datetime"
    val = (interaction.guild_id, interaction.user.id)
    mycursor.execute(sql, val)
    choiceList = []

    for deadlineID in mycursor:
        name = "(Due: " + str(deadlineID[2])[0:19] + \
            ")" + " Deadline Name: " + deadlineID[1]
        choiceList.append(app_commands.Choice(name=name, value=deadlineID[0]))

    if (len(choiceList) != 0):
        return choiceList
    else:
        choiceList.append(app_commands.Choice(name="You have nothing to do",
                                              value=0))
        return choiceList


# /suggestion_to
# 這個部分的功能是用modal進行的
# 如果要加入繪出表格的程式，建議放在on_submit裡頭
class SuggestChart(ui.Modal):
    def __init__(self, who_to_suggest: str, score: int, update: int, guild):
        super().__init__(title="Suggestion", timeout=None)
        self.who_to_suggest_id = int(who_to_suggest)
        self.score = score
        self.update = update
        self.suggestion = ui.TextInput(label=f'Suggestions to {client.get_guild(guild).get_member(self.who_to_suggest_id).display_name}**', placeholder='Blank is fine',
                                       required=False, max_length=100, style=discord.TextStyle.long)
        self.add_item(self.suggestion)

    async def on_submit(self, interaction: discord.Interaction):

        if (self.update == 0):
            sql = "INSERT INTO suggestion (`discordID`, `suggesterID`, `content`, `score`, `guild`) VALUES (%s, %s, %s, %s, %s)"
            val = (self.who_to_suggest_id, interaction.user.id,
                   self.suggestion.value, self.score, interaction.guild_id)
            mycursor.execute(sql, val)
            db.commit()
            msg = f'We have received your suggestion to {interaction.guild.get_member(self.who_to_suggest_id).display_name} :)\nscore: {self.score}\nsuggestion: {self.suggestion}'
            # await interaction.followup.send('123456798')

        else:
            sql = "UPDATE suggestion SET content=%s, score=%s WHERE discordID=%s AND suggesterID=%s AND guild=%s"
            val = (self.suggestion.value, self.score, self.who_to_suggest_id,
                   interaction.user.id, interaction.guild_id)
            mycursor.execute(sql, val)
            db.commit()
            msg = f'We have updated your suggestion to {interaction.guild.get_member(self.who_to_suggest_id).display_name} :)\nscore: {self.score}\nsuggestion: {self.suggestion}'

        await interaction.response.send_message(content=msg, ephemeral=True)


# 程式不建議放在這裡
@client.tree.command()
@app_commands.describe(
    who_to_suggest='select the person to suggest',
    overall_score='rate his/her performance, score from 1 to 10',
)
# 程式不建議放在這裡
@app_commands.choices(overall_score=choiceLList(1, 10))
async def suggestion_to(interaction: discord.Interaction, who_to_suggest: str, overall_score: discord.app_commands.Choice[int]):
    """匿名互評表"""
    sql = "SELECT * FROM suggestion WHERE discordID=%s AND suggesterID=%s AND guild=%s"
    val = (who_to_suggest, interaction.user.id, interaction.guild_id)
    mycursor.execute(sql, val)
    update = 0
    for x in mycursor:
        update = 1
    await interaction.response.send_modal(SuggestChart(who_to_suggest, overall_score.value, update, interaction.guild_id))
# 程式不建議放在這裡


@suggestion_to.autocomplete('who_to_suggest')
async def suggestion_to_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    choiceList = []
    for member in interaction.guild.members:
        if (member.id != interaction.user.id and member.bot != 1):
            choiceList.append(app_commands.Choice(
                name=member.display_name, value=str(member.id)))

    return choiceList
# 程式不建議放在這裡


@client.tree.command(description="印出分工表、甘特圖以及互評表")
@app_commands.describe(
    print_distribution_table='click yes to print out the work distribution table',
    print_gannt='click yes to print out the gannt chart',
    print_evaluation_table='click yes to print out the evaluation table made by your peers'
)
@app_commands.choices(print_distribution_table=[app_commands.Choice(name="Yes", value=1), app_commands.Choice(name="No", value=0)], print_gannt=[app_commands.Choice(name="Yes", value=1), app_commands.Choice(name="No", value=0)], print_evaluation_table=[app_commands.Choice(name="Yes", value=1), app_commands.Choice(name="No", value=0)])
async def whos_freerider(interaction: discord.Interaction, print_distribution_table: discord.app_commands.Choice[int], print_gannt: discord.app_commands.Choice[int], print_evaluation_table: discord.app_commands.Choice[int]):

    # 兩個防呆機制
    sql = "SELECT deadlineID FROM deadline WHERE guild=%s"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    repeat = mycursor.fetchall()
    if (len(repeat) == 0):
        # 防呆一：沒有任何專案資訊
        await interaction.response.send_message("You have nothing to print!")
        return

    if (print_distribution_table.value != 1 and print_evaluation_table.value != 1 and print_gannt.value != 1):
        # 防呆二：使用者沒有要印任何圖
        await interaction.response.send_message('Do not play around with me  ^_^')
        return

    await interaction.response.defer()  # extend response time for 15 mins

    # 以下處理，為了避免週期性專案重複名稱，影響甘特圖的繪製
    sql = "SELECT deadlineName FROM deadline WHERE guild=%s GROUP BY deadlineName HAVING count(*)>1;"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    repeat = mycursor.fetchall()

    returnList = []  # 0: 原本的名字 1: deadlineID

    # 把資料抓出來後，再重新改名加上重複次數後，塞回去 mySQL 中
    for i in repeat:
        sql = "SELECT deadlineID from deadline where deadlineName=%s and guild=%s"
        val = (i[0], interaction.guild_id)
        mycursor.execute(sql, val)
        deadlineID = mycursor.fetchall()
        count = 1
        for x in deadlineID:
            returnList.append((i[0], x[0]))
            sql = "UPDATE deadline SET deadlineName=%s WHERE deadlineID=%s"
            val = (i[0] + f'_{count}', x[0])
            mycursor.execute(sql, val)
            db.commit()
            count += 1

    # user chose to print out distribution table
    if(print_distribution_table.value == 1):
        sql = "SELECT user.name, deadline.deadlineName, userdeadline.status, deadline.datetime, userdeadline.end_time FROM user, deadline, userdeadline WHERE user.discordID=userdeadline.discordID and user.guild=deadline.guild and user.guild=%s and deadline.deadlineID=userdeadline.deadlineID Order by user.discordID, userdeadline.start_time"
        val = (interaction.guild_id, )
        mycursor.execute(sql, val)
        tableData = mycursor.fetchall()

        mergeData = [[0]*5 for i in range(len(tableData))]

        # copy data from tableData
        for i in range(len(tableData)):
            for j in range(len(tableData[i])):
                mergeData[i][j] = tableData[i][j]

        # change status into understandable words
        for i in range(len(mergeData)):
            if mergeData[i][2] == 2:
                mergeData[i][2] = 'be late'
            elif mergeData[i][2] == 1:
                mergeData[i][2] = 'on time'
            else:
                if mergeData[i][3] <= datetime.datetime.now():
                    mergeData[i][2] = 'be late'
                else:
                    mergeData[i][2] = 'not yet'

        # 分工表轉換為dataframe
        df = pd.DataFrame(mergeData, columns=[
            '作者姓名', '專案名稱', '繳交狀況', '應交時間', '繳交時間'])
        tableName = str(interaction.guild_id) + 'table' + '.png'
        df.dfi.export(tableName, fontsize=14)

        # 開啟分工表 png
        imTable = Image.open(tableName)
        wTable, hTable = imTable.size

        # 畫布
        img = Image.new(mode="RGB", size=(int(wTable + 40),
                                          int(hTable + 40)), color=(255, 255, 255))
        d = ImageDraw.Draw(img)

        # 將分工表格貼上畫布，轉存為 png 檔，接著再 followup 送出
        img.paste(imTable, (20, 20))  # distribution table
        fileName = fileName = str(interaction.guild_id) + 'table' + '.png'
        img.save(fileName, save_all=True)
        await interaction.followup.send(file=discord.File(fileName))

    # users chose to print out gannt charts
    if (print_gannt.value == 1):
        # 兩段工作，第一段處理使用者個人的甘特圖，第二段處理團體的甘特圖
        # 此處開啟 table 是為了後續甘特圖調整大小用，實際上不會在此輸出
        tableName = str(interaction.guild_id) + 'table' + '.png'
        imTable = Image.open(tableName)
        wTable, hTable = imTable.size

    #!!!以下我們首先處理個人的甘特圖!!!
        # fetch data from userdeadline
        sql = "SELECT * FROM userdeadline ORDER BY discordID"
        mycursor.execute(sql)
        data = mycursor.fetchall()

        user_list = []
        user_out_list = []

        # 先從 userdeadline 中找出要被輸出的使用者，並且排除重複的資料
        for i in range(len(data)):
            if data[i][1] not in user_list:
                user_list.append(data[i][1])

        for u in user_list:
            # 再次確定要輸出的使用者，確保其在該伺服器內，且 discordID 相同
            sql = "SELECT name FROM user WHERE discordID = '%s' AND guild=%s" % (
                u, interaction.guild_id)
            mycursor.execute(sql)
            result = mycursor.fetchall()

            # 萬一遇到有使用者資料不齊全就跳過
            if (len(result) == 0):
                continue

            # user_out_list 是確定會出書的使用者清單
            user_out_list.append(u)

            name = result[0][0]
            deadline_this_user = []
            status_this_user = []
            starttime_this_user = []
            endtime_this_user = []
            datetime_this_user = []

            # 再將該名使用者各deadline詳細資料完整查出
            sql = "SELECT deadlineID, status, start_time, end_time  FROM userdeadline WHERE discordID = '%s'" % (
                u)
            mycursor.execute(sql)
            result = mycursor.fetchall()

            for x in result:
                # 定位 deadline 的來源伺服器
                sql = "SELECT guild from deadline WHERE deadlineID=%s" % (x[0])
                mycursor.execute(sql)
                result2 = mycursor.fetchall()

                # 若「該專案來源伺服器」與「目前要求輸出的伺服器」不同，就跳過
                if(result2[0][0] != str(interaction.guild_id)):
                    continue
                else:  # 否，則將資料都存入先前建立的清單
                    deadline_this_user.append(x[0])
                    status_this_user.append(x[1])
                    starttime_this_user.append(x[2])
                    endtime_this_user.append(x[3])

            # 再將繳交狀態改成用中文表達
            for i in range(len(status_this_user)):
                if(status_this_user[i]) == 1:
                    status_this_user[i] = '準時繳交'
                if(status_this_user[i]) == 2:
                    status_this_user[i] = '遲交'
                if(status_this_user[i]) == 0:
                    status_this_user[i] = '未交'

            # 將 deadlineID 改成以 deadlineName 表達，同時也記錄下應交時間
            for i in range(len(deadline_this_user)):
                sql = "SELECT deadlineName, datetime FROM deadline WHERE deadlineID=%s AND guild=%s" % (
                    deadline_this_user[i], interaction.guild_id)
                mycursor.execute(sql)
                result2 = mycursor.fetchall()
                for y in result2:
                    deadline_this_user[i] = y[0]
                    datetime_this_user.append(y[1])

            # 此時建立 table
            table = {
                "任務": deadline_this_user,
                "任務開始時間": starttime_this_user,
                "任務結束時間": datetime_this_user,
                "實際繳交時間": endtime_this_user,
                "繳交狀況": status_this_user
            }

            # 轉成dataframe形式後以matplotlib繪製成甘特圖
            df = pd.DataFrame(table)
            df['任務時長0'] = df['任務結束時間'] - df['任務開始時間']
            df['任務時長'] = (df["任務時長0"]).dt.days
            proj_start = df['任務開始時間'].min()
            df['start_num'] = (df['任務開始時間'] - proj_start).dt.days
            df['end_num'] = (df['任務結束時間'] - proj_start).dt.days

            colors2 = {'準時繳交': '#00AA00', '遲交': '#FF8800', '未交': '#FF3333'}

            def color(row):
                return colors2[row['繳交狀況']]

            df = pd.DataFrame(table)
            df['任務時長0'] = df['任務結束時間'] - df['任務開始時間']
            df['任務時長'] = (df["任務時長0"]).dt.total_seconds() / \
                timedelta(days=1).total_seconds()
            proj_start = df['任務開始時間'].min()
            df['start_num'] = (
                df['任務開始時間'] - proj_start).dt.total_seconds() / timedelta(days=1).total_seconds()
            df['end_num'] = (df['任務結束時間'] - proj_start).dt.total_seconds() / \
                timedelta(days=1).total_seconds()

            colors2 = {'準時繳交': '#00AA00', '遲交': '#FF8800', '未交': '#FF3333'}

            def color(row):
                return colors2[row['繳交狀況']]

            df['color'] = df.apply(color, axis=1)
            df = df.sort_values(by='start_num', ascending=False)
            fig, ax = plt.subplots(1, figsize=(16, 6))
            ax.barh(df['任務'], df['任務時長'], left=df.start_num, color=df.color)
            f = str(u)+".xlsx"
            df.to_excel(f)

            # 顏色標籤
            legend_elements = [Patch(facecolor=colors2[i], label=i)
                               for i in colors2]
            plt.legend(handles=legend_elements)

            total_length = df.end_num.max() - df.start_num.min()
            slic = 1
            if total_length > 7:
                slic = int(total_length/5)

            # x軸改成日期
            xticks = np.arange(0, df.end_num.max(), slic)
            xticks_labels = pd.date_range(
                proj_start, end=df['任務結束時間'].max()).strftime("%m/%d %H:%M:%S")
            xticks_minor = np.arange(0, df.end_num.max(), 1)
            ax.set_xticks(xticks)
            ax.set_xticks(xticks_minor, minor=True)
            if(total_length < 1):
                ax.set_xticklabels(xticks_labels[:len(xticks):1])
            else:
                ax.set_xticklabels(xticks_labels[::slic])
            title = "Gantt chart of " + name
            plt.title(title, fontsize=25)
            plt.xlabel("Date", fontsize=20)
            plt.ylabel("Deadline Name", fontsize=20)
            plt.yticks(size=18)
            plt.xticks(size=15)
            personal_ganntName = str(u) + 'PersonalGannt.png'
            plt.savefig(personal_ganntName)

            # 最後繪製成圖片檔
            ax = plt.axes()
            ax.set_facecolor("gray")

            # open gannt chart
            tempGantt = Image.open(personal_ganntName)

            # resize by the width of gannt chart, set its max width by distribution table's
            # then, save it
            wGantt, hGantt = tempGantt.size
            if wGantt > wTable:
                hGantt = hGantt*(wTable/wGantt)
                wGantt = wTable
                resizeImgGantt = tempGantt.resize((int(wGantt), int(hGantt)))
                resizeImgGantt.save(personal_ganntName)

        for u in user_out_list:
            personal_gannt_search = str(u) + 'PersonalGannt' + '.png'
            personal_gannt_search_img = Image.open(personal_gannt_search)
            personal_gannt_search_w, personal_gannt_search_h = personal_gannt_search_img.size
            img = Image.new(mode="RGB", size=(int(wTable + 40),
                            int(personal_gannt_search_h + 40)), color=(255, 255, 255))
            img.paste(personal_gannt_search_img, (20, 20))
            # save img as a png file
            fileName = str(u) + 'PersonalGannt' + '.png'
            img.save(fileName, save_all=True)
            # send the png
            await interaction.followup.send(file=discord.File(fileName))

    #!!!以下處理團體甘特圖!!!
        # 取出所有來自該伺服器的專案
        sql = "SELECT deadlineID FROM deadline WHERE guild=%s"
        val = (interaction.guild_id, )
        mycursor.execute(sql, val)
        result = mycursor.fetchall()
        deadline_list = []

        # 將取出的 deadlineID 塞進 deadline_list 清單中
        for i in range(len(result)):
            deadline_list.append(result[i][0])

        name_list = []
        status_list = []
        starttime_list = []
        datetime_list = []
        # 根據 deadlineID 蒐集其名稱、應教時間、繳交狀態，並一一放進所對應的清單中
        for u in deadline_list:
            sql = "SELECT deadlineName, datetime, status FROM deadline WHERE deadlineID = '%s'" % (
                u)
            mycursor.execute(sql)
            result = mycursor.fetchall()
            name = result[0][0]
            name_list.append(name)
            datetime_list.append(result[0][1])
            status_list.append(result[0][2])

            # 同樣根據 deadlineID 取出開始時間，放入對應的清單中
            sql = "SELECT start_time FROM userdeadline WHERE deadlineID = '%s'" % (
                u)
            mycursor.execute(sql)
            result = mycursor.fetchall()
            starttime_list.append(result[0][0])

        # 將繳交狀態修改為中文
        for i in range(len(status_list)):
            if(status_list[i]) == 1:
                status_list[i] = '已完成'
            if(status_list[i]) == 2:
                status_list[i] = '遲交'
            if(status_list[i]) == 0:
                status_list[i] = '未完成'

        # 建立table
        table = {
            "任務": name_list,
            "任務開始時間": starttime_list,
            "任務結束時間": datetime_list,
            "繳交狀況": status_list
        }

        # 轉換成 dataframe，以利製作甘特圖
        df = pd.DataFrame(table)

        # 將所需資料轉換處理、調色
        df['任務時長0'] = df['任務結束時間'] - df['任務開始時間']
        df['任務時長'] = (df["任務時長0"]).dt.days

        proj_start = df['任務開始時間'].min()
        df['start_num'] = (df['任務開始時間'] - proj_start).dt.days
        df['end_num'] = (df['任務結束時間'] - proj_start).dt.days
        colors2 = {'已完成': '#00AA00', '未完成': '#E63F00'}

        def color(row):
            return colors2[row['繳交狀況']]

        df = pd.DataFrame(table)
        df['任務時長0'] = df['任務結束時間'] - df['任務開始時間']
        df['任務時長'] = (df["任務時長0"]).dt.total_seconds() / \
            timedelta(days=1).total_seconds()
        proj_start = df['任務開始時間'].min()
        df['start_num'] = (
            df['任務開始時間'] - proj_start).dt.total_seconds() / timedelta(days=1).total_seconds()
        df['end_num'] = (df['任務結束時間'] - proj_start).dt.total_seconds() / \
            timedelta(days=1).total_seconds()

        colors2 = {'已完成': '#00AA00', '未完成': '#E63F00'}

        def color(row):
            return colors2[row['繳交狀況']]

        df['color'] = df.apply(color, axis=1)
        df = df.sort_values(by='start_num', ascending=False)
        fig, ax = plt.subplots(1, figsize=(16, 6))
        ax.barh(df['任務'], df['任務時長'], left=df.start_num, color=df.color)
        f = str(interaction.guild_id)+".xlsx"
        df.to_excel(f)

        # 顏色標籤
        legend_elements = [Patch(facecolor=colors2[i], label=i)
                           for i in colors2]
        plt.legend(handles=legend_elements)

        total_length = df.end_num.max() - df.start_num.min()
        slic = 1
        if total_length > 7:
            slic = int(total_length/5)

        # x軸改成日期
        xticks = np.arange(0, df.end_num.max(), slic)
        xticks_labels = pd.date_range(
            proj_start, end=df['任務結束時間'].max()).strftime("%m/%d %H:%M:%S")
        xticks_minor = np.arange(0, df.end_num.max(), 1)
        ax.set_xticks(xticks)
        ax.set_xticks(xticks_minor, minor=True)
        if(total_length < 1):
            ax.set_xticklabels(xticks_labels[:len(xticks):1])
        else:
            ax.set_xticklabels(xticks_labels[::slic])

        title = "Gantt chart of " + interaction.guild.name
        plt.title(title, fontsize=25)
        plt.xlabel("Date", fontsize=20)
        plt.ylabel("Deadline Name", fontsize=20)
        plt.yticks(size=18)
        plt.xticks(size=15)
        guild_ganntName = str(interaction.guild_id) + 'GuildGannt' + '.png'
        plt.savefig(guild_ganntName)
        ax = plt.axes()
        ax.set_facecolor("gray")

        # open gannt chart
        tempGantt = Image.open(guild_ganntName)

        # resize by the width of gannt chart, set its max width by distribution table's
        # then, save it
        wGantt, hGantt = tempGantt.size
        if wGantt > wTable:
            hGantt = hGantt*(wTable/wGantt)
            wGantt = wTable
            resizeImgGantt = tempGantt.resize((int(wGantt), int(hGantt)))
            resizeImgGantt.save(guild_ganntName)

        # here print it out
        guild_gannt_search = str(interaction.guild_id) + 'GuildGannt' + '.png'
        guild_gannt_search_img = Image.open(guild_gannt_search)
        guild_gannt_search_w, guild_gannt_search_h = guild_gannt_search_img.size
        img = Image.new(mode="RGB", size=(int(wTable + 40),
                        int(guild_gannt_search_h + 40)), color=(255, 255, 255))
        img.paste(guild_gannt_search_img, (20, 20))
        # save img as a png file
        fileName = str(interaction.guild_id) + 'GuildGannt' + '.png'
        img.save(fileName, save_all=True)
        # send the png
        await interaction.followup.send(file=discord.File(fileName))

    # user chose to print out evaluation table
    if (print_evaluation_table.value == 1):

        # fetch data from suggestion
        guildID = interaction.guild_id
        sql = 'SELECT * FROM suggestion WHERE guild=%s ORDER BY discordID'
        val = (guildID, )
        mycursor.execute(sql, val)
        data = mycursor.fetchall()
        howManyRows = mycursor.rowcount

        # fetch data from user
        sql = 'SELECT * FROM user WHERE guild=%s ORDER BY discordID'
        val = (guildID, )
        mycursor.execute(sql, val)
        user = mycursor.fetchall()
        howManyUsers = mycursor.rowcount

        # 0 = discordID, 1 = how many times she been graded
        howManyHasBeenGrade = [[0, 0]*1 for i in range(howManyUsers)]
        # 計算使用者被評分幾次，用來平均分數
        for i in range(howManyUsers):
            checkWhoBeenGrade = user[i][0]
            gradeTimes = 0
            for j in range(howManyRows):
                if data[j][0] == checkWhoBeenGrade:
                    gradeTimes += 1
            howManyHasBeenGrade[i][0] = checkWhoBeenGrade

            if gradeTimes > 0:
                howManyHasBeenGrade[i][1] = gradeTimes
            else:
                howManyHasBeenGrade[i][1] = 1  # 設定 1 避免平均時分母為零

        dataToSend = [[0]*3 for i in range(howManyUsers)]
        # copy name, calculate average score, and sum all comments
        for i in range(howManyUsers):
            tempID = user[i][0]
            tempScore = 0
            tempComment = ''
            for j in range(howManyRows):
                if tempID == data[j][0]:
                    tempScore += data[j][3]
                    tempComment = tempComment + data[j][2] + '. '

            # average score
            denomitator = 1
            for x in range(len(howManyHasBeenGrade)):
                if tempID == howManyHasBeenGrade[x][0]:
                    denomitator = howManyHasBeenGrade[x][1]
                    break

            tempScore /= (denomitator)
            dataToSend[i][0] = user[i][1]  # user's name
            dataToSend[i][1] = float(tempScore)  # avg score
            dataToSend[i][2] = str(tempComment)  # comments

        # dataframe
        pd.set_option('max_colwidth', 30)  # set maxmimum width of column
        suggestionChartFile = str(guildID) + 'Suggestion.png'
        df = pd.DataFrame(dataToSend, columns=['Name', 'Score', 'Content'])

        # dataframe export
        df.dfi.export(suggestionChartFile, fontsize=14)

        # plot
        suggestionChart = Image.open(suggestionChartFile)
        wSuggest, hSuggest = suggestionChart.size
        widthA = 536
        heightA = int(hSuggest * (536 / wSuggest))
        new_suggestionChart = suggestionChart.resize(
            (int(widthA), int(heightA)))
        new_wSuggest, new_hSuggest = new_suggestionChart.size

        img = Image.new(mode="RGB", size=(new_wSuggest + 40,
                                          new_hSuggest + 40), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        img.paste(new_suggestionChart, (20, 20))
        img.save(suggestionChartFile, save_all=True)

        # to_excel
        csvName = str(guildID) + 'Suggestion.csv'
        df.to_csv(csvName, index=False, columns=[
                  'Name', 'Score', 'Content'], encoding='utf-8-sig')

        await interaction.followup.send(file=discord.File(suggestionChartFile))
        await interaction.followup.send(file=discord.File(csvName))

    # 最一開始修改資料，只是為了暫時輸出用，最後還是把資料變成原先的樣態
    for i in range(len(returnList)):
        sql = "UPDATE deadline SET deadlineName=%s WHERE deadlineID=%s"
        val = (returnList[i][0], returnList[i][1])
        mycursor.execute(sql, val)
        db.commit()


client.run(TOKEN)
