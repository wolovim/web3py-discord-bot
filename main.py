import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from web3 import AsyncWeb3, WebSocketProvider
from eth_abi.abi import decode

# If you want insight into the underlying websocket:
import logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WSS_URL_MAINNET = os.getenv("WSS_URL_MAINNET")
WSS_URL_SEPOLIA = os.getenv("WSS_URL_SEPOLIA")
WSS_URL_OP = os.getenv("WSS_URL_OP")
STARTING_CHANNEL_ID = os.getenv("STARTING_CHANNEL_ID")
ART_BLOCKS_ADDRESS = "0xa7d8d9ef8d8ce8992df33d8b8cf4aebabd5bd270"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

w3_mainnet = AsyncWeb3(WebSocketProvider(WSS_URL_MAINNET))
# w3_sepolia = AsyncWeb3(WebSocketProvider(WSS_URL_SEPOLIA))
w3_optimism = AsyncWeb3(WebSocketProvider(WSS_URL_OP))

NETWORKS = {
    "mainnet": w3_mainnet,
    # "sepolia": w3_sepolia,
    "optimism": w3_optimism,
}

active_subscriptions = {
    # This will get populated during bot usage, e.g.:
    # "mainnet": {"newHeads": subscription_id_1, "transfers": subscription_id_2},
    # "optimism": {"newHeads": subscription_id_3, "transfers": subscription_id_4},
    # "sepolia": {"newHeads": subscription_id_5, "transfers": subscription_id_6},
    network: {}
    for network in NETWORKS.keys()
}


def _network_log(msg, network="mainnet"):
    return f"[{network.upper()}]: {msg}"


@bot.event
async def on_ready():
    channel = bot.get_channel(int(STARTING_CHANNEL_ID)) if STARTING_CHANNEL_ID else None
    if channel is not None:
        await channel.send(f"Deployed {bot.user.name}")

    for name, w3 in NETWORKS.items():
        await w3.provider.connect()

        if channel is not None:
            await channel.send(f"Connected to {name}")

    if channel is not None:
        await channel.send(f"Use `!listen <network>` to listen for subscriptions")


@bot.command()
async def connect_all(ctx):
    for name, w3 in NETWORKS.items():
        if not await w3.provider.is_connected():
            await w3.provider.connect()
            await ctx.send(f"Connected to {name}")
        else:
            await ctx.send(f"Already connected to {name}")


@bot.command()
async def ping(ctx):
    """Ping the bot"""
    await ctx.send("pong")


def handle_new_header(header, network):
    return _network_log(
        f"**[Block: {header['number']}]** Gas limit: "
        f"{header['gasUsed'] / header['gasLimit'] * 100:.2f}%",
        network,
    )


async def handle_new_transfer(transfer, network="mainnet"):
    # example log:
    # AttributeDict({
    #   'address': '0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270',
    #   'topics': [
    #       HexBytes('0xddf252...'),            # topic
    #       HexBytes('0x000000...64d22dca'),    # from address
    #       HexBytes('0x000000...91465944'),    # to address
    #       HexBytes('0x000000...002dcd7c')     # token id
    #   ],
    #   'data': HexBytes('0x'),
    #   'blockNumber': 18429127,
    #   'transactionHash': HexBytes('0xece65d0...8be7cde'),
    #   'transactionIndex': 152,
    #   'blockHash': HexBytes('0xcb801a...b82ad5c7'),
    #   'logIndex': 404,
    #   'removed': False
    # })
    token_id = decode(["uint256"], transfer["topics"][3])[0]
    from_addr = decode(["address"], transfer["topics"][1])[0]
    to_addr = decode(["address"], transfer["topics"][2])[0]
    message = _network_log(
        f"{from_addr[:8]}... transferred Art Blocks token "
            f"[{token_id}](<https://etherscan.io/nft/{ART_BLOCKS_ADDRESS}/{token_id}>) to {to_addr[:8]}... in "
        f"block [{transfer['blockNumber']}](<https://etherscan.io/tx/{transfer['transactionHash'].hex()}>)",
        network,
    )
    return message


@bot.command()
async def listen(ctx, network="mainnet"):
    """Listen for subscriptions"""
    await ctx.send(
        _network_log("Listening for subscriptions in this channel...", network)
    )
    w3 = NETWORKS[network]
    while True:
        try:
            async for payload in w3.socket.process_subscriptions():
                # standard payload: {"subscription": "{id}", "result": "{payload}"}
                if "subscription" not in payload:
                    logging.debug(f"\n∆∆∆ non-standard payload: {payload}")
                    continue

                subscription_name = None
                network_active_subs = active_subscriptions.get(network)
                if network_active_subs is not None:
                    for name, sub_id in network_active_subs.items():
                        if sub_id == payload["subscription"]:
                            subscription_name = name
                            break

                if subscription_name is None:
                    logging.debug(
                        _network_log(
                            f"Unrecognized subscription: {payload['subscription']}",
                            network,
                        )
                    )
                    continue
                elif subscription_name == "newHeads":
                    message = handle_new_header(payload["result"], network)
                    await ctx.send(message)
                elif subscription_name == "transfers":
                    message = await handle_new_transfer(payload["result"], network)
                    asyncio.create_task(ctx.send(message))
                else:
                    logging.debug(f"{network.upper()} | wat? {payload['subscription']}")
                    continue
        except Exception as e:
            logging.debug(_network_log(f"Exception in listener: {e}", network))
            logging.debug(e.__class__.__name__)
            await asyncio.sleep(3)  # Wait before attempting to reconnect


@bot.command("subs")
async def view_subscriptions(ctx):
    """View active subscriptions"""
    await ctx.send(f"Active subscriptions: {active_subscriptions}")


@bot.command("cancel")
async def cancel_subscription(ctx, subscription_name, network="mainnet"):
    """Unsubscribe from a subscription"""
    w3 = NETWORKS[network]
    network_subs = active_subscriptions.get(network)
    try:
        unsubscribed = await w3.eth.unsubscribe(network_subs[subscription_name])
        if unsubscribed:
            network_subs.pop(subscription_name)
            await ctx.send(
                _network_log(f"Unsubscribed from {subscription_name}", network)
            )
            await ctx.send(f"Active subscriptions: {active_subscriptions}")
        else:
            await ctx.send(
                _network_log(f"Failed to unsubscribe from {subscription_name}", network)
            )
    except Exception as e:
        await ctx.send(f"Error: {e}")


@bot.command("newHeads")
async def add_headers_subscription(ctx, network="mainnet"):
    """Add a newHeads subscription"""
    w3 = NETWORKS[network]

    network_subs = active_subscriptions.get(network)

    if "newHeads" not in network_subs:
        headers_subscription_id = await w3.eth.subscribe("newHeads")
        active_subscriptions[network]["newHeads"] = headers_subscription_id
        await ctx.send(
            _network_log(
                "Subscribed to newHeads with id " f"{headers_subscription_id}", network
            )
        )
    else:
        await ctx.send(
            _network_log(
                f"Already subscribed to newHeads with id {network_subs['newHeads']}",
                network,
            )
        )


@bot.command()
async def transfers(ctx, network="mainnet"):
    """Add an Art Blocks Transfer subscription"""
    if network != "mainnet":
        await ctx.send(
            _network_log(
                "Example log subscription to Art Blocks Transfer events is only available on mainnet.",
                network,
            )
        )
        return
    w3 = NETWORKS[network]

    transfer_event_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
    filter_params = {
        "address": ART_BLOCKS_ADDRESS,
        "topics": [transfer_event_topic],
    }

    if "transfers" not in active_subscriptions[network]:
        subscription_id = await w3.eth.subscribe("logs", filter_params)
        active_subscriptions[network]["transfers"] = subscription_id
        await ctx.send(
            _network_log(f"Subscribed to transfers with id {subscription_id}", network)
        )
    else:
        await ctx.send(
            _network_log(
                "Already subscribed to transfers with id "
                f"{active_subscriptions['transfers']}",
                network,
            )
        )


@bot.command()
async def balance(ctx, address, network="mainnet"):
    """Get the balance of an account"""
    w3 = NETWORKS[network]

    try:
        balance = await w3.eth.get_balance(address)
        await ctx.send(
            _network_log(f'{w3.from_wei(balance, "ether"):.4f} ether', network)
        )
    except Exception as e:
        await ctx.send(_network_log(f"Error: {e}", network))


@bot.command()
async def block(ctx, block_number, network="mainnet"):
    """Get the gas utilization and transaction count for a block"""
    w3 = NETWORKS[network]

    block_identifiers = ["latest", "earliest", "pending", "safe", "finalized"]
    if block_number not in block_identifiers:
        try:
            block_number = int(block_number)
        except ValueError:
            await ctx.send(
                _network_log(f"Error: Invalid block number {block_number}.", network)
            )
            return

    b = await w3.eth.get_block(block_number)
    await ctx.send(
        _network_log(
            f"**[Block: {b.number}]**"
            f" Gas limit: {b.gasUsed / b.gasLimit * 100:.2f}%"
            f" - Txs: {len(b.transactions)}",
            network,
        )
    )


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
