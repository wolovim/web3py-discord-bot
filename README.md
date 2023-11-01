# web3py-discord-bot

A Discord bot reference repo leveraging the newly rewritten
[web3.py](https://web3py.readthedocs.io/en/stable/) websocket provider,
`WebsocketProviderV2`, which includes `eth_subscribe` support.

This bot can listen for subscriptions on a particular channel or execute one-off
requests, like retrieving a balance or some block data.

The bot's architecture can support multiple chains. It will default to mainnet,
but you can add `sepolia` or `optimism` to the end of any command to interact
with those networks instead (if you include valid URLs in your `.env` file).

### One-off commands

One-off commands can be run in any channel that the bot has access to, for
example:

- `!block latest sepolia` - to return some data about the latest sepolia testnet
  block
- `!balance shaq.eth` - to return an ether balance (ENS supported)

### Subscriptions

The user flow for subscriptions is to:

1. Tell the bot which channel to listen for messages in (`!listen`)
1. Create a new subscription (`!newHeads, !transfers`)
1. View your active subscriptions (`!subs`)
1. Unsubscribe (`!cancel newHeads`, `!cancel transfers`)

A couple of sample subscription commands are included:

- `!newHeads` will start a subscription watching for new block headers
- `!transfers` will watch for new `Transfer` events from the Art Blocks NFT
  contract

  <img width="843" alt="Screenshot 2023-11-01 at 10 45 32 AM" src="https://github.com/wolovim/web3py-discord-bot/assets/3621728/86d06b9d-ea41-45ec-b146-b1e241150dca">

## Setup

- Follow `discord.py` directions to
  [create a bot account](https://discordpy.readthedocs.io/en/stable/discord.html)
  on Discord. By the end you'll have a `token`.
- Create your `.env` file to pass secrets into the app
  - Use the `.env.example` file to reference the key names
  - Store your newly created `token` as `DISCORD_TOKEN`
  - Add your websocket URL(s) to connect to a node
  - Optional: include the
    [channel ID](https://docs.statbot.net/docs/faq/general/how-find-id) of a
    channel you'd like to see startup messages in
- Install dependencies: `pip install -r requirements.txt`
- Start the bot in a terminal: `python snekbot.py`
- Use the bot. Try `!help` to view a list of commands.
- Bonus: host your bot! You can only do so much from your local machine.

## Disclaimer

This bot is for educational purposes only and does not aspire to be anything
robustly production-grade. Hopefully it's a good starting point for your
hackathon project or next adventure.

That said,

- the web3.py team wants your feedback on `WebsocketProviderV2`! Open an
  [issue](https://github.com/ethereum/web3.py) if you encounter one, or share
  your experience in the Ethereum Python Community
  [Discord](https://discord.gg/GHryRvPB84).
- I'm happy to field suggestions or bug reports in this repo. Open issues as you
  see fit.
