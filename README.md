# Discord Bot

Personal discord bot that has some basic utility commands that you might find with other bots. A couple unique commands is the ability to lookup an Overwatch player's statistics via a third party API, as well as the ability to set announcements for Twitch streamers whenever they go live using the Twitch API.

# Commands / Usage

- /ping : Pong!
- /avatar : Displays the specified user's avatar
- /8ball : Ask the magic 8-ball a question!  
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
‎   
- /overwatch [player] : Lookup an overwatch player's statistics for the most recent season.
- /overwatch [player] [hero] : Look up an overwatch player's statistics for a specific hero for the most recent season.
