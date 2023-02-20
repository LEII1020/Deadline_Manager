import datetime
from dateutil.relativedelta import relativedelta  # 需額外安裝 python-dateutil 函式庫

oddList = [1, 3, 5, 7, 8, 10, 12]
doubleList = [4, 6, 9, 11]


def TheDateDoesNotExist(Y, M, D):
    Y = int(Y)
    M = int(M)
    D = int(D)
    if (M in oddList):
        if (D > 31):
            return True
        else:
            return False
    elif (M in doubleList):
        if (D > 30):
            return True
        else:
            return False
    else:
        if (Y % 400 == 0 or (Y % 4 == 0 and Y % 100 != 0)):
            if (D > 29):
                return True
            else:
                return False
        else:
            if (D > 28):
                return True
            else:
                return False


def TheLastDayOfMonth(Y, M):
    Y = int(Y)
    M = int(M)
    if (M in oddList):
        return 31
    elif (M in doubleList):
        return 30
    else:
        if (Y % 400 == 0 or (Y % 4 == 0 and Y % 100 != 0)):
            return 29
        else:
            return 28


def TimeHasNotPassTheDestTime(now, Dest):
    '''判斷此刻時間是否已經超過目標時間。未超過便回傳True'''
    if (now.hour < Dest.hour or (now.hour == Dest.hour and now.minute < Dest.minute) or (now.hour == Dest.hour and now.minute == Dest.minute and (now.second - Dest.second > 0))):
        return True
    else:
        return False


def GetExactDate(frequency, fday, ftime):
    '''取得本次deadline的確切時間'''
    now = datetime.datetime.now()
    destTime = datetime.time(
        int(ftime.split(":")[0]), int(ftime.split(":")[1]), 0, 0)
    fday = int(fday)

    if (frequency == "allDay"):  # 每天提醒的狀況
        if (TimeHasNotPassTheDestTime(now.time(), destTime)):
            now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                ftime.split(":")[1]), second=0)
            return now
        else:
            now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                ftime.split(":")[1]), second=0)
            return now + datetime.timedelta(days=1)
    elif (frequency == "everyWeek"):  # 每周提醒的狀況
        if (fday < now.isoweekday()):  # 繳交期限為下一周
            temp = 7 - (now.isoweekday() - fday)
            now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                ftime.split(":")[1]), second=0)
            return now + datetime.timedelta(days=temp)
        else:  # 繳交期限為本周
            if ((fday - now.isoweekday()) > 0):
                temp = fday - now.isoweekday()
                now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                    ftime.split(":")[1]), second=0)
                return now + datetime.timedelta(days=temp)
            else:  # 繳交期限為本日
                if (TimeHasNotPassTheDestTime(now.time(), destTime)):
                    now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                        ftime.split(":")[1]), second=0)
                    return now
                else:
                    now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                        ftime.split(":")[1]), second=0)
                    return now + datetime.timedelta(days=7)
    else:  # 每月提醒的狀況
        # 這個月已過截止期限，繳交期限為下個月
        if (fday < now.day or (fday == now.day and not (TimeHasNotPassTheDestTime(now.time(), destTime)))):
            if (TheDateDoesNotExist(now.year, now.month + 1, fday)):  # 下個月不存在該日期
                now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                    ftime.split(":")[1]), second=0)
                return now + relativedelta(months=+1)
            else:
                now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                    ftime.split(":")[1]), second=0)
                return (now + relativedelta(months=+1)).replace(day=fday)
        else:  # 這個月未過期限，繳交期限為本月
            if (TheDateDoesNotExist(now.year, now.month, fday)):  # 這個月不存在該日期
                now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                    ftime.split(":")[1]), second=0)
                return now.replace(day=TheLastDayOfMonth(now.year, now.month))
            else:
                temp = fday - now.day
                now = now.replace(hour=int(ftime.split(":")[0]), minute=int(
                    ftime.split(":")[1]), second=0)
                return now + datetime.timedelta(days=temp)
