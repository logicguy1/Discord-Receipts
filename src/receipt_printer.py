from escpos.printer import Network
from PIL import Image
import requests
from io import BytesIO
from datetime import datetime
import sys


class ReceiptPrinter:
    """Manages printing Discord messages to a thermal receipt printer."""

    def __init__(self, ip: str, port: int = 9100, width: int = 80):
        """
        Initialize the receipt printer.

        Args:
            ip: IP address of the network printer
            port: Port number (default: 9100 for thermal printers)
            width: Character width for text wrapping (default: 80)
        """
        self.ip = ip
        self.port = port
        self.width = width
        print(f'Printer configured for {ip}:{port}', file=sys.stderr)

    def _connect(self) -> Network | None:
        """
        Establish a connection to the printer.

        Returns:
            Network printer instance or None if connection fails
        """
        try:
            return Network(self.ip, self.port)
        except Exception as e:
            print(f'Failed to connect to printer at {self.ip}:{self.port}: {e}', file=sys.stderr)
            return None

    def _download_and_process_avatar(self, avatar_url: str, size: int = 80) -> Image.Image | None:
        """
        Download and process a Discord avatar for printing.

        Args:
            avatar_url: URL of the Discord avatar
            size: Size of the avatar in pixels (default: 80x80)

        Returns:
            Processed PIL Image or None if failed
        """
        try:
            response = requests.get(avatar_url, timeout=5)
            if response.status_code == 200:
                # Open image and convert to grayscale
                img = Image.open(BytesIO(response.content))
                img = img.convert('L')

                # Resize to specified size
                img = img.resize((size, size), Image.Resampling.LANCZOS)

                # Convert to black and white with dithering
                img = img.convert('1')

                return img
        except Exception as e:
            print(f'Could not fetch/process avatar: {e}', file=sys.stderr)
            return None

    def _download_and_process_image(self, image_url: str, max_width: int = 384) -> Image.Image | None:
        """
        Download and process an image attachment for printing.

        Args:
            image_url: URL of the image
            max_width: Maximum width in pixels (default: 384 for thermal printers)

        Returns:
            Processed PIL Image or None if failed
        """
        try:
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                # Open image and convert to grayscale
                img = Image.open(BytesIO(response.content))
                img = img.convert('L')

                # Calculate new dimensions maintaining aspect ratio
                aspect_ratio = img.height / img.width
                new_width = min(img.width, max_width)
                new_height = int(new_width * aspect_ratio)

                # Resize image
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Convert to black and white with dithering
                img = img.convert('1')

                return img
        except Exception as e:
            print(f'Could not fetch/process image: {e}', file=sys.stderr)
            return None

    def print_message(self, message, target_user_id: int):
        """
        Print a Discord message to the receipt printer.

        Args:
            message: Discord message object
            target_user_id: ID of the user being monitored
        """
        # Connect to printer for this print job
        printer = self._connect()
        if not printer:
            return

        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            is_mention = any(user.id == target_user_id for user in message.mentions)

            # Check for role mentions
            is_role_mention = False
            if message.guild and message.role_mentions:
                target_member = message.guild.get_member(target_user_id)
                if target_member:
                    target_role_ids = {role.id for role in target_member.roles}
                    mentioned_role_ids = {role.id for role in message.role_mentions}
                    is_role_mention = bool(target_role_ids & mentioned_role_ids)

            # Check for @everyone or @here
            is_everyone = message.mention_everyone

            is_reply = (message.reference and
                       message.reference.resolved and
                       message.reference.resolved.author.id == target_user_id)

            # Server/Channel header
            self._print_channel_header(printer, message)

            # Reply indicator if applicable
            if is_reply:
                self._print_reply_indicator(printer, message.reference.resolved)

            # Small profile picture on the left
            self._print_avatar(printer, message.author.display_avatar.url)

            # Author name and timestamp on same line
            self._print_author_line(printer, message.author.display_name, timestamp, is_mention, is_role_mention, is_everyone)

            # Message content
            self._print_content(printer, message.content)

            # Print image attachments if any
            self._print_attachments(printer, message)

            # Separator
            self._print_separator(printer)

        except Exception as e:
            print(f'Error printing to receipt printer: {e}', file=sys.stderr)
        finally:
            # Close the connection
            try:
                printer.close()
            except:
                pass

    def _print_channel_header(self, printer, message):
        """Print server/channel header."""
        printer.set(align='left', font='b', bold=True)
        if message.guild:
            printer.text(f'# {message.channel.name}\n')
            printer.set(font='b', bold=False)
            printer.text(f'{message.guild.name}\n')
        else:
            printer.text('DIRECT MESSAGE\n')
        printer.text('\n')

    def _print_reply_indicator(self, printer, replied_message):
        """Print reply indicator."""
        printer.set(align='left', font='b', bold=False)
        printer.text(f'  Replying to {replied_message.author.name}\n')
        printer.text('\n')

    def _print_avatar(self, printer, avatar_url: str):
        """Print the user's small avatar on the left."""
        img = self._download_and_process_avatar(avatar_url, size=64)
        if img:
            printer.set(align='left')
            printer.image(img, impl='bitImageColumn')

    def _print_author_line(self, printer, author_name: str, timestamp: str, is_mention: bool, is_role_mention: bool = False, is_everyone: bool = False):
        """Print author name and timestamp."""
        printer.set(align='left', font='a', bold=True)

        # Author name
        printer.text(f'{author_name}')

        # Mention badges
        printer.set(bold=False)
        if is_mention:
            printer.text(' @')

        if is_role_mention:
            printer.text(' @role')

        if is_everyone:
            printer.text(' @everyone')

        # Timestamp
        printer.set(bold=False)
        printer.text(f'  {timestamp}\n')

    def _print_content(self, printer, content: str):
        """Print the message content with word wrapping."""
        printer.set(align='left', font='a', bold=False)

        # Word wrap for long messages
        words = content.split()
        line = ""
        for word in words:
            if len(line + word) < self.width:
                line += word + " "
            else:
                printer.text(line + '\n')
                line = word + " "
        if line:
            printer.text(line + '\n')

    def _print_attachments(self, printer, message):
        """Print image attachments from the message."""
        if not message.attachments:
            return

        # Filter for image attachments
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        image_attachments = [
            att for att in message.attachments
            if any(att.filename.lower().endswith(ext) for ext in image_extensions)
        ]

        if not image_attachments:
            return

        # Add spacing before images
        printer.text('\n')

        # Print each image attachment
        for attachment in image_attachments:
            printer.set(align='left', font='b', bold=False)
            printer.text(f'[Image: {attachment.filename}]\n')

            img = self._download_and_process_image(attachment.url)
            if img:
                printer.set(align='center')
                printer.image(img, impl='bitImageColumn')
                printer.text('\n')
            else:
                printer.text('(Failed to load image)\n')

    def _print_separator(self, printer):
        """Print a separator line and cut."""
        printer.cut()
