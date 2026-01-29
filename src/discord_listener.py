import discord
import os
import sys
from receipt_printer import ReceiptPrinter

# Printer configuration
PRINTER_IP = "192.168.1.81"
PRINTER_PORT = 9100
PRINTER_WIDTH = 60  # Character width for receipts

# Target user ID to monitor
TARGET_USER_ID = 936357105760370729

# Create printer instance
receipt_printer = ReceiptPrinter(PRINTER_IP, PRINTER_PORT, PRINTER_WIDTH)

# Create a self-bot client (for user accounts)
client = discord.Client()

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}#{client.user.discriminator} (ID: {client.user.id})', file=sys.stderr)
    print('Listening for messages...', file=sys.stderr)
    print('-' * 50, file=sys.stderr)

@client.event
async def on_message(message):
    # Check if the message mentions the target user or is a DM to them
    should_print = False

    # Check if it's a DM
    if not message.guild:
        should_print = True
    else:
        # Check if the target user is mentioned directly
        if any(user.id == TARGET_USER_ID for user in message.mentions):
            should_print = True

        # Check if a role is mentioned that the target user has
        if message.role_mentions:
            # Get the target user's member object in this guild
            target_member = message.guild.get_member(TARGET_USER_ID)
            if target_member:
                # Check if any mentioned role is in the target user's roles
                target_role_ids = {role.id for role in target_member.roles}
                mentioned_role_ids = {role.id for role in message.role_mentions}
                if target_role_ids & mentioned_role_ids:  # Set intersection
                    should_print = True

        # Check for @everyone or @here mentions
        if message.mention_everyone:
            should_print = True

        # Check if it's a reply to a message from the target user
        if message.reference and message.reference.resolved:
            if message.reference.resolved.author.id == TARGET_USER_ID:
                should_print = True

    # Print if relevant
    if should_print:
        # Build output text for stdout
        if message.guild:
            mention_type = ""
            if any(user.id == TARGET_USER_ID for user in message.mentions):
                mention_type = " [MENTION]"
            if message.reference and message.reference.resolved:
                if message.reference.resolved.author.id == TARGET_USER_ID:
                    mention_type += " [REPLY]"

            output_text = f'[{message.guild.name}#{message.channel.name}]{mention_type} {message.author.name}: {message.content}'
        else:
            output_text = f'[DM] {message.author.name}: {message.content}'

        # Print to stdout
        print(output_text)
        sys.stdout.flush()

        # Print to receipt printer
        receipt_printer.print_message(message, TARGET_USER_ID)

if __name__ == '__main__':
    # Get token from environment variable or command line
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        if len(sys.argv) > 1:
            token = sys.argv[1]
        else:
            print('Error: No Discord token provided!', file=sys.stderr)
            print('Usage: python discord_listener.py <token>', file=sys.stderr)
            print('   or: DISCORD_TOKEN=<token> python discord_listener.py', file=sys.stderr)
            sys.exit(1)

    # Start the self-bot
    try:
        client.run(token)  # bot=False for user accounts
    except discord.LoginFailure:
        print('Error: Invalid Discord token!', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
