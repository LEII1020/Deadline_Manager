# 官方的函式庫
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import tasks
import mysql.connector
import random
from time import sleep
from typing import Optional


# 自己的函式
import period_function  # 與period deadline有關的function全部放在這邊 # 需額外安裝 python-dateutil 函式庫


# 還沒做的事情：
#   防呆機制


# mysql的設定
db = mysql.connector.connect(
    host='localhost',
    user='root',
    passwd='',  # 自己填入資料庫密碼
    database='dm'
)
mycursor = db.cursor(buffered=True)
# mysql的設定結束


# discord的設定
# # 要記得在discord portal的Bot將PRESENCE INTENT、SERVER MEMBERS INTENT、MESSAGE CONTENT INTENT給打開
TOKEN = ''  # 自己填入TOKEN
MY_GUILD = discord.Object(id=0)  # 自己填入guild id


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


intents = discord.Intents.default()
intents.members = True
client = MyClient(intents=intents)
# discord的設定結束


# 放入toNotify
def InsertToNotify(dest: datetime, deadlineID: int):
    # """放入到toNotify表格"""
    now = datetime.datetime.now()
    sql = "INSERT INTO `toNotify` (`deadlineID`, `Ndatetime`, `num`) VALUES (%s, %s, %s)"
    result = dest-now
    if (result.seconds > 86403):  # 目前時間離deadline截止時間還有超過一天
        val = (deadlineID, dest - datetime.timedelta(days=1), 5)
        mycursor.execute(sql, val)
        db.commit()
    if (result.seconds > 21603):  # 目前時間離deadline截止時間還有超過6小時
        val = (deadlineID, dest - datetime.timedelta(hours=6), 4)
        mycursor.execute(sql, val)
        db.commit()
    if (result.seconds > 3603):  # 目前時間離deadline截止時間還有超過1小時
        val = (deadlineID, dest - datetime.timedelta(hours=1), 3)
        mycursor.execute(sql, val)
        db.commit()
    if (result.seconds > 183):  # 目前時間離deadline截止時間還有超過3分鐘
        val = (deadlineID, dest - datetime.timedelta(minutes=3), 2)
        mycursor.execute(sql, val)
        db.commit()
    val = (deadlineID, dest, 1)
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
# 放入userdeadline結束


@tasks.loop(seconds=1)
async def task():
    now = datetime.datetime.now()
    sql = "SELECT * from toNotify WHERE Ndatetime BETWEEN %s and %s ORDER BY Ndatetime"
    val = (now, now + datetime.timedelta(microseconds=50))
    mycursor.execute(sql, val)

    temp = []  # 裝接下來要訊息發送的toNotify表格裡的資料
    tempmsg = []  # 裝接下來要發送的文字訊息

    for x in mycursor:
        temp.append(x)

    sql = "DELETE from toNotify WHERE Ndatetime < %s"  # 將Notify中已經過期的資料給刪除掉
    val = (now + datetime.timedelta(microseconds=50), )
    mycursor.execute(sql, val)
    db.commit()

    if (len(temp) != 0):

        remindmsg = ["", "is overdue\n🔥🔥🔥🔥🔥", "is about to due in 3 minutes\n🔥🔥🔥",
                     "is about to due in 1 hour\n🔥", "is about to due in 6 hours", "is about to due in 24 hours"]

        for x in temp:  # 先找出與toNotify的deadlineID相符合的userdeadline資料
            deadlineID = x[0]
            allMen = []
            tempMem = []
            sql = "SELECT discordID, status from userdeadline WHERE deadlineID=%s ORDER BY discordID"
            val = (deadlineID, )
            mycursor.execute(sql, val)
            for xx in mycursor:  # 在userdeadline表格中，將要提醒的使用者資料加入到tempMem中
                allMen.append(xx[0])
                if (xx[1] == 0):
                    tempMem.append(client.get_user(int(xx[0])).mention)

            sql = "SELECT channel, PN, periodID, deadlineName, guild, channel from deadline WHERE deadlineID=%s"
            val = (deadlineID, )
            mycursor.execute(sql, val)
            # 進到deadline表格，並存取要傳出的訊息、頻道、PN、periodID、deadline名稱、伺服器以及頻道
            for xx in mycursor:
                if (len(tempMem) != 0):  # 如果有成員尚未完成
                    tempmsg.append(
                        [f'Hey! {" ".join(tempMem)}\n{xx[3]} {remindmsg[x[2]]}\n_______________', xx[0], xx[1], xx[2], xx[3], xx[4], xx[5]])
                elif (len(tempMem) == 0 and x[2] == 1):  # 如果成員都已經完成
                    tempmsg.append(
                        [f'Looks like everyone has finish the mission--{xx[3]}, good job!\n_______________', xx[0], xx[1], xx[2], xx[3], xx[4], xx[5]])

            if (x[2] == 1):  # 如果是最後一次提醒
                # Period deadline需先將下期的資料重新創制並放入deadline中(代表deadline中會保存每一期的period deadline資料)，接著再重新創制userdeadline，最後再放入toNotify中
                if (tempmsg[-1][2] == "P"):

                    # 先找到該筆period deadline的週期以及下一期的時間
                    sql = "SELECT frequency, day, time From periodDeadline WHERE periodID=%s"
                    val = (tempmsg[-1][3], )
                    mycursor.execute(sql, val)
                    for xx in mycursor:
                        ExactDate = period_function.GetExactDate(
                            xx[0], xx[1], str(xx[2]))

                    tempmsg[-1].append(ExactDate)

                    # 將period_deadline存進deadline
                    sql = "INSERT INTO `deadline` (`periodID`, `deadlineName`, `PN`, `datetime`, `status`, `guild`, `channel`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    val = (tempmsg[-1][3], tempmsg[-1][4], 'P',
                           ExactDate, '0', tempmsg[-1][5], tempmsg[-1][6])
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

                    tempmsg[-1].append(allMen)

        for x in tempmsg:
            await client.get_channel(int(x[1])).send(x[0])
            if (x[2] == 'P'):
                await client.get_channel(int(x[6])).send(f'Mission: {x[4]}\nDeadline(period): {str(x[7])}\nMember: {x[8]}')


# '''登錄提醒'''


@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    task.start()


# 功能: /start
@client.tree.command()
async def start(interaction: discord.Interaction):
    '''將成員的名字與ID存入資料庫 名字會顯示在分工成果表上'''
    sql = "INSERT IGNORE INTO `user` (`name`, `discordID`) VALUES (%s, %s)"
    for member in interaction.guild.members:
        val = (member.name, member.id)
        mycursor.execute(sql, val)
    db.commit()
    await interaction.response.send_message(f'Finish Data upload :)')


# 功能: /changer_name
@client.tree.command()
@app_commands.describe(  # 向使用者說明各欄位的填入格式
    name='the name that show on the work distribution chart (word limit:20)'
)
async def changer_name(interaction: discord.Interaction, name: str):
    '''更改顯示在分工成果表上的名字'''
    if (len(name) > 20):  # 查看是否超過字數上限
        await interaction.response.send_message(f'{name} exceeds the limit :(', ephemeral=True)
        return
    sql = "SELECT * FROM user WHERE discordID=%s"
    val = (interaction.user.id)
    mycursor.execute(sql, val)
    for x in mycursor:  # 查看mysql 中是否有該位使用者存在
        sql = "UPDATE user SET name=%s WHERE discordID=%s"
        val = (name, interaction.user.id)
        mycursor.execute(sql, val)
        db.commit()
        await interaction.response.send_message(f'successfully update your name to {name} :)', ephemeral=True)
        return
    await interaction.response.send_message(f'looks like your guild haven\'t use the function /'/start/', please use it first', ephemeral=True)


# 功能: /deadline_cancel 要注意讓使用者不要刪掉其他伺服器的deadline #如果要刪掉整個period deadline 要記得將deadline的PN欄位調整成N
"""@client.tree.command() 
@app_commands.describe(  # 向使用者說明各欄位的填入格式
    deadlineID='the deadline which you want to cancel'
    period_deadlineID='the period deadline which you want to cancel'
)
async def deadline_cancel(interaction: discord.Interaction, deadlineID: int=None, period_deadlineID: int=None):"""


# 功能: /set_deadline
@client.tree.command()
@app_commands.describe(  # 向使用者說明各欄位的填入格式
    date='yyyy-mm-dd',
    time='hh:mm',
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
    if (time.count(":") != 1):
        failmsg.append("wrong time format. (correct example: 00:33)")
    if (int(time.split(":")[0]) < 0 or int(time.split(":")[0]) > 23):
        failmsg.append("wrong hour")
    if (int(time.split(":")[1]) < 0 or int(time.split(":")[1]) > 59):
        failmsg.append("wrong minute")
    member_or_members = member_or_members.split()
    for x in member_or_members:
        if (("<" not in x) or ("@" not in x) or (">" not in x)):
            failmsg.append(
                "wrong member format, you just need to @someone")
            break
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

    now = datetime.datetime.now()

    if (dest < now):
        await interaction.channel.send(f'⚠️You have enter a past date for deadline')

    # 該deadline放入userdeadline
    for x in range(len(member_or_members)):
        InsertToUserdeadline(deadlineID=deadlineID,
                             member=member_or_members[x])
        member_or_members[x] = client.get_user(
            int(member_or_members[x])).mention
    member_or_members = " ".join(member_or_members)
    # 該deadline放入userdeadline結束

    await interaction.response.send_message(f'Mission: {mission_name}\nDeadline: {date} {time}\nMember: {member_or_members}')


# 功能: /set_period_deadline
@client.tree.command()
@app_commands.describe(  # 向使用者說明各欄位的填入格式
    period='allDay(remind everyday)/ everyWeek(remind once a week)/ everyDate(remind once a month)',
    period_day='allDay: enter 0/ everyWeek: choose from 1 to 7/ everyDate: choose from 1 to 31',
    time='hh:mm',
    mission_name='what is your deadline about? (describe spicificly)',
    member_or_members='@someone @someone @someone (it\'s fine if there\'s only one member in this mission',
)
@app_commands.choices(period=[
    discord.app_commands.Choice(name='allDay', value='allDay'),
    discord.app_commands.Choice(name='everyWeek', value='everyWeek'),
    discord.app_commands.Choice(name='everyDate', value='everyDate'),
])
async def set_period_deadline(interaction: discord.Interaction, period: discord.app_commands.Choice[str], period_day: int, time: str, mission_name: str, member_or_members: str):
    """設定Deadline"""

    # 防呆機制
    failmsg = []
    if (period == "allDay" and period_day != 0):
        failmsg.append(
            "wrong period_day, please enter 0 in period_day if you want to be remined everyday")
    elif (period == "everyWeek" and (period_day < 1 or period_day > 7)):
        failmsg.append(
            "wrong period_day, please enter a number between 1 to 7 in period_day if you want to be remined everyweek\n(1 for Monday, 2 for Tuesday...etc.)")
    elif (period == "everyWeek" and (period_day < 1 or period_day > 31)):
        failmsg.append("wrong period_day, please enter a number between 1 to 31 in period_day if you want to be remined everymonth\n(if the date you choose doesn\'t exist in the month, we're remind you in that month\'s last day)")
    if (time.count(":") != 1):
        failmsg.append("wrong time format. (correct example: 00:33)")
    if (int(time.split(":")[0]) < 0 or int(time.split(":")[0]) > 23):
        failmsg.append("wrong hour")
    if (int(time.split(":")[1]) < 0 or int(time.split(":")[1]) > 59):
        failmsg.append("wrong minute")
    member_or_members = member_or_members.split()
    for x in member_or_members:
        if (("<" not in x) and ("@" not in x) and (">" not in x)):
            failmsg.append(
                "wrong member format, you just need to enter @someone, and don't forget to put a space between each members")
            break
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
    date = period_function.GetExactDate(str(period.name), period_day, time)
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
        InsertToUserdeadline(deadlineID=deadlineID,
                             member=member_or_members[x])
        member_or_members[x] = client.get_user(
            int(member_or_members[x])).mention
    member_or_members = " ".join(member_or_members)
    # 放入userdeadline結束

    await interaction.response.send_message(f'Mission: {mission_name}\nDeadline(period): {date} {time}\nMember: {member_or_members}')


# /my_deadline
@client.tree.command()
# 向使用者說明各欄位的填入格式
@app_commands.describe(show_all='click yes to show all deadline(incluing from other guild), else click no')
@app_commands.choices(show_all=[
    discord.app_commands.Choice(name='yes', value=1),
    discord.app_commands.Choice(name='no', value=0),
])
async def mydeadline(interaction: discord.Interaction, show_all: discord.app_commands.Choice[int]):
    """查看使用者尚未完成的Deadline，只有該使用者可見"""
    member = interaction.user.id
    if (show_all.value == 1):  # 顯示所有deadline
        sql = "SELECT deadline.PN, deadline.deadlineName, deadline.datetime, deadline.guild, deadline.deadlineID FROM deadline, userdeadline WHERE userdeadline.discordID=%s and deadline.deadlineID=userdeadline.deadlineID and userdeadline.status=0 ORDER BY deadline.datetime"
        val = (member, )
    else:
        sql = "SELECT deadline.PN, deadline.deadlineName, deadline.datetime, deadline.guild, deadline.deadlineID FROM deadline, userdeadline WHERE userdeadline.discordID=%s and deadline.deadlineID=userdeadline.deadlineID and userdeadline.status=0 and deadline.guild=%s ORDER BY deadline.datetime"
        val = (member, interaction.guild_id)

    mycursor.execute(sql, val)
    msg = "Good to see you " + str(client.get_user(int(member)).name) + \
        " :)\nThis is your deadline\n--------------------------------------\n"

    now = datetime.datetime.now()

    for x in mycursor:

        if (x[2] < now):
            msg += "\t⚠️This mission is overdue\n"
        msg += "\tDeadlineID: " + str(x[4]) + "\n"

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

    if (msg == "Good to see you " + str(client.get_user(int(member)).name) + " :)\nThis is your deadline\n--------------------------------------\n"):
        msg = "Good to see you " + \
            str(client.get_user(int(member)).name) + \
            " :)\nYou have no deadline now, "
        list = ("go water your plant!", "go feed your cat!", "go find yourself something to do!", "just relax!", "go eat something!",
                "go play jigsaw puzzle!", "go out to the great outdoors!", "go play fetch with your dog!", "go make your mama some cookies!")
        msg += list[random.randrange(len(list))]

    await interaction.response.send_message(content=msg, ephemeral=True)


# /check
@client.tree.command(description="To check all of the deadline\'s status")
async def check(interaction: discord.Interaction):
    msg = "Good to see you " + interaction.user.name + " :)\nThose are the deadline from " + \
        interaction.guild.name + "\n--------------------------------------\n"

    jokelist = ("", "", "", ", Good Jod! Nobody:3", "", "", "", "", "")

    guildDeadline = []
    sql = "SELECT deadlineID, deadlineName, PN, datetime, status FROM deadline WHERE guild=%s ORDER BY datetime"
    val = (interaction.guild_id, )
    mycursor.execute(sql, val)
    for x in mycursor:
        guildDeadline.append(x)

    for x in guildDeadline:
        if (x[3] < datetime.datetime.now()):
            msg += "\t⚠️This mission is overdue\n"

        msg += "\tDeadlineID: " + str(x[0]) + "\n"

        if (x[2] == 'N'):
            msg += "\tMission: " + str(x[1]) + " (Normal)\n"
        else:
            msg += "\tMission: " + str(x[1]) + " (Period)\n"

        msg += "\tDue: " + str(x[3]) + "\n"

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
                    finish.append(client.get_user(int(xx[0])).name)
            if (len(finish) == 0):
                msg += "Nobody has finish this deadline" + \
                    jokelist[random.randrange(
                        len(jokelist))] + "\n--------------------------------------\n"
            else:
                msg += "Unfinish members: " + " ".join(unfinish) + "\n"
                msg += "Finish members: " + \
                    " ".join(finish) + \
                    "\n--------------------------------------\n"
        else:
            msg += "\tMission has been successfully completed 😎" + \
                "\n--------------------------------------\n"

    if (msg == "Good to see you " + interaction.user.name + " :)\nThose are the deadline from " +
            interaction.guild.name + "\n--------------------------------------\n"):
        msg = "Good to see you " + interaction.user.name + " :)\nThose is no deadline in " + \
            interaction.guild.name + ", looks like it's time to create a new mission!"

    await interaction.response.send_message(content=msg)


# /mission_complete
@client.tree.command()
@app_commands.describe(
    deadlineID='which deadline do you now finish? please enter your deadlineID, if you don\'t know, just enter 0',
)
async def mission_complete(interaction: discord.Interaction, deadlineID: str, your_attachment: discord.Attachment = None):
    '''完成任務'''
    if (deadlineID == 0):
        """查看使用者尚未完成的Deadline，只有該使用者可見"""
        member = interaction.user.id
        sql = "SELECT deadline.PN, deadline.deadlineName, deadline.datetime, deadline.guild, deadline.deadlineID FROM deadline, userdeadline WHERE userdeadline.discordID=%s and deadline.deadlineID=userdeadline.deadlineID and userdeadline.status=0 and deadline.guild=%s ORDER BY deadline.datetime"
        val = (member, interaction.guild_id)

        mycursor.execute(sql, val)
        msg = "Good to see you " + str(client.get_user(int(member)).name) + \
            " :)\nThis is your deadline\n--------------------------------------\n"

        now = datetime.datetime.now()

        for x in mycursor:

            if (x[2] < now):
                msg += "\t⚠️This mission is overdue\n"

            msg += "\tDeadlineID: " + str(x[4]) + "\n"

            if (x[0] == 'N'):
                msg += "\tMission: " + str(x[1]) + " (Normal)\n"
            else:
                msg += "\tMission: " + str(x[1]) + " (Period)\n"

            msg += "\tDue: " + str(x[2]) + \
                "\n--------------------------------------\n"

        if (msg == "Good to see you " + str(client.get_user(int(member)).name) + " :)\nThis is your deadline\n--------------------------------------\n"):
            msg = "Good to see you " + \
                str(client.get_user(int(member)).name) + \
                " :)\nYou have no deadline now"

        await interaction.response.send_message(content=msg, ephemeral=True)

    else:  # 要記得將status=1的notify刪到只剩到期時的提醒
        sql = "UPDATE userdeadline SET status=1, end_time=%s WHERE discordID=%s AND deadlineID=%s"
        val = (datetime.datetime.now(), int(interaction.user.id), deadlineID)
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


client.run(TOKEN)
