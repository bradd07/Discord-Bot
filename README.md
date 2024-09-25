# Discord Bot

Personal discord bot that has some basic utility commands that you might find with other bots. A couple unique commands is the ability to lookup an Overwatch player's statistics via a third party API, as well as the ability to set announcements for Twitch streamers whenever they go live via the Twitch API.

Don't want to set it up on your own? [Add my bot to your server!](https://discord.com/api/oauth2/authorize?client_id=1049242812119535636&permissions=8&scope=applications.commands+bot)

# Setup
Step one - Create a [Discord application](https://discord.com/developers/applications) (if necessary)  

Step two - Create a [Twitch application](https://dev.twitch.tv/console) (if necessary)  

Step three - Clone the repository
```
$ git clone https://github.com/bradd07/Discord-Bot.git
```
Step four - Install required packages
```
$ pip3 install -r requirements.txt
```
Step five - Modify the .env file accordingly from steps one/two  
```
TWITCH_CLIENT_ID=your twitch client ID
TWITCH_ACCESS_TOKEN=your twitch access token (will generate for the first time if empty/invalid)
BOT_TOKEN=your discord application token
TWITCH_SECRET=your twitch secret ID
```
Step six - Run
```
$ python3 main.py
```

# Commands / Usage

- /ping : Pong!
- /avatar : Displays the specified user's avatar
- /8ball : Ask the magic 8-ball a question!  
- /poll create [choice1] [choice2] [...] : Start a poll with up to 10 choices
- /purge [count] : Delete a number of messages (limit 50)  
‎   
- /reactionrole add [emoji] [role] [message_id] : Add a reaction role to a message  
- /reactionrole remove [emoji] [message_id] : Remove a reaction role from a message  
- /reactionrole clear [message_id] : Clear all reaction roles from a message  
All data is saved locally to a JSON file.  
‎   
- /points : Display your own or the specified user's current amount of points in this guild
- /setpoints [user] [amount] : Set the specified user's total amount of points in this guild
- /addpoints [user] [amount] : Add points to the specified user's total in this guild
- /givepoints [user] [amount] : Give some of your own points to another player in the same guild
- /leaderboard : Display the top 5 users with the most amount of points for this guild
- /raffle [amount] [duration] : Create a raffle for free points for this guild
- /join : Join the active raffle for this guild\
All data is saved locally to a JSON file.  
‎   
- /twitch add [username] : Add a twitch streamer to the list so that an announcement is made when they go live for this guild
- /twitch remove [username] : Remove a twitch streamer from the list for this guild
- /twitch list : List the streamers this guild is announcing for
- /twitch setchannel [id] : Set the channel to send the announcements in
- /twitch force [username] : Force an announcement to the channel for the specified streamer in this guild\
All data is saved locally to a JSON file.  
NOTE: Although we try to make an announcement every time a new stream starts, we also don't want to spam servers with announcements. Therefore, there is a hard limit of one announcement per streamer every six hours.  
‎   
- /overwatch [player] : Lookup an overwatch player's statistics for the most recent season.
- /overwatch [player] [hero] : Look up an overwatch player's statistics for a specific hero for the most recent season.
