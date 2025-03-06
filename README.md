# :wave: Deadline Manager Deadline管理器

## 🤖 Deadline Manager介紹

一個管理 Deadline 的小工具，由一群來自文院管院社科院的學生們所製作。
功能包含設定Deadline提醒、設定週期性Deadline提醒、印出分工表甘特圖互評表...等等。

## 📖 使用方式 ( Mac 可能會難以操作本程式)

需要先設置自己的機器人，請上 [Discord Portal - Application](https://discord.com/developers/applications)上進行申請。本程式在 OAuth2 上需要的權限有：Manage Channels、Read Messages/View Channels、Send Message、Attach Files、Use Slash Commands。Bot 欄位中的 PRESENCE INTENT、SERBER MEMBERS INTENT、MESSAGE CONTENT INTENT 也要記得開啟。

接著要設立自己的 MySQL 資料庫，這部分網路上也有許多的影片教學，不贅述。

安裝所有 main.py 中引入的函式庫

使用 DM_MYSQL.txt 直接設置 dm 資料庫

將 Bot 的 Token 碼放入 main.py 的 49 行，並於 36-41 行填寫相關的資料庫設定。

啟用後，將 Bot 邀請入 Discord 的伺服器中即可開始使用。

## 📦 使用的函式庫

主要：discord.py

其他：datetime、matploblib、numpy、pandas、PIL、win32com


