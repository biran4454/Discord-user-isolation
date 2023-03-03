## Summary
Use `/isolate` to send a user to their own channel, where they can still receive messages from #general via. the bot. Any messages they send will be relayed to a verification channel where admins can allow or deny the message with the click of a button.

The bot supports using the GPT-3 AI to automatically allow or deny messages*. Admins can also block any isolated user from sending messages, to prevent spamming the verification channel.  
If isolated users start spamming the verification channel, use `/lockdown-isolated` to mute all isolated members. Beware though to undo this an admin must unblock each, one by one.

\* currently uses my API key. If demand improves, a system may be set up for servers to use their own API key.  
Note: if ai support is turned on, all messages from isolated users will be sent to GPT-3 for reviewal. There is no guarantee that this is 100% effective and it may produce false positives or false negatives. I give no warranty that this system will work and that they messages will be secure. In testing, it has worked very well, so it should be ok.

## Commands

The bot supports both discord slash commands, and the prefix `iso`  
Key: [permission] - Permission required to use the command  
`/isolate <user>` [timeout] - Isolate a user from the server  
`/unisolate <user>` [timeout] - Remove a user from isolation  
`/block-isolated <user>` [timeout] - Block a user from sending messages in their isolated channel  
`/unblock-isolated <user>` [timeout] - Unblock a user from sending messages in their isolated channel  
`/lockdown-isolated` [administrator] - Block all isolated users from sending messages. Caution: to undo this, you must manually unblock each isolated user  
`/enable-ai` [administrator] - Enable AI for this server  
`/disable-ai` [administrator] - Disable AI for this server  
`/ping` - Get the bot’s latency  
`/info` - Get info about the bot  
`/help` - Show commands reference  

NB: `/setup` and `/setup-role` must be run when the bot is first added, to create the verification channel, isolation category, and isolated role.

## Privacy
If `/enable-ai` is run, the ID of your server will be stored in a file on the bot’s server. This will (unless in the case of an error) be deleted if you run /disable-ai.  
Apart from that collected by GPT-3 when AI is turned on, I do not knowingly store any other personal information or infomation in your server.