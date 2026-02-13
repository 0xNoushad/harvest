"""
Interactive UI Elements

Pagination, confirmations, and interactive keyboard components.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional, Callable, Any, Dict
from dataclasses import dataclass
from .formatters import EmojiFormatter


@dataclass
class PaginationConfig:
    """Configuration for pagination."""
    items_per_page: int = 10
    show_page_numbers: bool = True
    show_item_count: bool = True
    show_jump_buttons: bool = False


class Paginator:
    """Handle pagination for lists of items."""
    
    def __init__(
        self,
        items: List[Any],
        config: Optional[PaginationConfig] = None
    ):
        """
        Initialize paginator.
        
        Args:
            items: List of items to paginate
            config: Pagination configuration
        """
        self.items = items
        self.config = config or PaginationConfig()
        self.total_items = len(items)
        self.total_pages = max(1, (self.total_items + self.config.items_per_page - 1) // self.config.items_per_page)
    
    def get_page(self, page: int) -> List[Any]:
        """
        Get items for a specific page.
        
        Args:
            page: Page number (1-indexed)
        
        Returns:
            List of items for the page
        """
        page = max(1, min(page, self.total_pages))
        start_idx = (page - 1) * self.config.items_per_page
        end_idx = start_idx + self.config.items_per_page
        return self.items[start_idx:end_idx]
    
    def get_page_info(self, page: int) -> str:
        """
        Get page information text.
        
        Args:
            page: Current page number
        
        Returns:
            Page info string (e.g., "Page 1 of 5 | Showing 1-10 of 47")
        """
        page = max(1, min(page, self.total_pages))
        start_idx = (page - 1) * self.config.items_per_page + 1
        end_idx = min(page * self.config.items_per_page, self.total_items)
        
        parts = []
        
        if self.config.show_page_numbers:
            parts.append(f"Page {page} of {self.total_pages}")
        
        if self.config.show_item_count:
            parts.append(f"Showing {start_idx}-{end_idx} of {self.total_items}")
        
        return " | ".join(parts)
    
    def get_keyboard(
        self,
        page: int,
        callback_prefix: str = "page"
    ) -> InlineKeyboardMarkup:
        """
        Get pagination keyboard.
        
        Args:
            page: Current page number
            callback_prefix: Prefix for callback data
        
        Returns:
            InlineKeyboardMarkup with pagination buttons
        """
        page = max(1, min(page, self.total_pages))
        buttons = []
        
        # Navigation row
        nav_row = []
        
        # First page button (if not on first page and jump buttons enabled)
        if self.config.show_jump_buttons and page > 1:
            nav_row.append(
                InlineKeyboardButton("⏮️ First", callback_data=f"{callback_prefix}_1")
            )
        
        # Previous button
        if page > 1:
            nav_row.append(
                InlineKeyboardButton("◀️ Previous", callback_data=f"{callback_prefix}_{page-1}")
            )
        
        # Page indicator
        nav_row.append(
            InlineKeyboardButton(f"• {page}/{self.total_pages} •", callback_data="page_info")
        )
        
        # Next button
        if page < self.total_pages:
            nav_row.append(
                InlineKeyboardButton("Next ▶️", callback_data=f"{callback_prefix}_{page+1}")
            )
        
        # Last page button (if not on last page and jump buttons enabled)
        if self.config.show_jump_buttons and page < self.total_pages:
            nav_row.append(
                InlineKeyboardButton("Last ⏭️", callback_data=f"{callback_prefix}_{self.total_pages}")
            )
        
        buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)
    
    def format_page(
        self,
        page: int,
        formatter: Callable[[Any, int], str],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> str:
        """
        Format a page of items.
        
        Args:
            page: Page number
            formatter: Function to format each item (item, index) -> str
            header: Optional header text
            footer: Optional footer text
        
        Returns:
            Formatted page text
        """
        items = self.get_page(page)
        page_info = self.get_page_info(page)
        
        parts = []
        
        if header:
            parts.append(header)
            parts.append("")
        
        # Format items
        start_idx = (page - 1) * self.config.items_per_page
        for i, item in enumerate(items):
            parts.append(formatter(item, start_idx + i))
        
        parts.append("")
        parts.append(page_info)
        
        if footer:
            parts.append("")
            parts.append(footer)
        
        return "\n".join(parts)


class ConfirmationDialog:
    """Create confirmation dialogs with customizable options."""
    
    @staticmethod
    def create(
        title: str,
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        confirm_callback: str = "confirm",
        cancel_callback: str = "cancel",
        warning: bool = False,
        details: Optional[Dict[str, str]] = None
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Create a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Main message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            confirm_callback: Callback data for confirm
            cancel_callback: Callback data for cancel
            warning: Whether to show warning emoji
            details: Optional key-value details to display
        
        Returns:
            Tuple of (message_text, keyboard)
        """
        emoji = EmojiFormatter.ALERT if warning else EmojiFormatter.INFO_ICON
        
        parts = [f"{emoji} **{title}**", "", message]
        
        if details:
            parts.append("")
            for key, value in details.items():
                parts.append(f"**{key}:** {value}")
        
        text = "\n".join(parts)
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{EmojiFormatter.SUCCESS} {confirm_text}",
                    callback_data=confirm_callback
                )
            ],
            [
                InlineKeyboardButton(
                    f"{EmojiFormatter.ERROR} {cancel_text}",
                    callback_data=cancel_callback
                )
            ]
        ])
        
        return text, keyboard
    
    @staticmethod
    def create_yes_no(
        title: str,
        message: str,
        yes_callback: str = "yes",
        no_callback: str = "no",
        warning: bool = False
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Create a yes/no confirmation dialog.
        
        Args:
            title: Dialog title
            message: Main message
            yes_callback: Callback data for yes
            no_callback: Callback data for no
            warning: Whether to show warning emoji
        
        Returns:
            Tuple of (message_text, keyboard)
        """
        return ConfirmationDialog.create(
            title=title,
            message=message,
            confirm_text="Yes",
            cancel_text="No",
            confirm_callback=yes_callback,
            cancel_callback=no_callback,
            warning=warning
        )
    
    @staticmethod
    def create_multi_option(
        title: str,
        message: str,
        options: List[tuple[str, str]],
        warning: bool = False
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Create a multi-option dialog.
        
        Args:
            title: Dialog title
            message: Main message
            options: List of (button_text, callback_data) tuples
            warning: Whether to show warning emoji
        
        Returns:
            Tuple of (message_text, keyboard)
        """
        emoji = EmojiFormatter.ALERT if warning else EmojiFormatter.INFO_ICON
        text = f"{emoji} **{title}**\n\n{message}"
        
        buttons = [
            [InlineKeyboardButton(text, callback_data=callback)]
            for text, callback in options
        ]
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        return text, keyboard


class MenuBuilder:
    """Build interactive menus with multiple options."""
    
    def __init__(self, title: str):
        """
        Initialize menu builder.
        
        Args:
            title: Menu title
        """
        self.title = title
        self.sections: List[tuple[str, List[tuple[str, str, Optional[str]]]]] = []
    
    def add_section(
        self,
        section_title: Optional[str] = None,
        items: Optional[List[tuple[str, str, Optional[str]]]] = None
    ) -> 'MenuBuilder':
        """
        Add a section to the menu.
        
        Args:
            section_title: Optional section title
            items: List of (text, callback, emoji) tuples
        
        Returns:
            Self for chaining
        """
        self.sections.append((section_title or "", items or []))
        return self
    
    def add_item(
        self,
        text: str,
        callback: str,
        emoji: Optional[str] = None,
        section_index: int = -1
    ) -> 'MenuBuilder':
        """
        Add an item to a section.
        
        Args:
            text: Button text
            callback: Callback data
            emoji: Optional emoji prefix
            section_index: Section to add to (-1 for last)
        
        Returns:
            Self for chaining
        """
        if not self.sections:
            self.sections.append(("", []))
        
        self.sections[section_index][1].append((text, callback, emoji))
        return self
    
    def build(
        self,
        columns: int = 2,
        include_back: bool = False,
        back_callback: str = "back"
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Build the menu.
        
        Args:
            columns: Number of columns for buttons
            include_back: Whether to include back button
            back_callback: Callback data for back button
        
        Returns:
            Tuple of (message_text, keyboard)
        """
        # Build message text
        text_parts = [f"{EmojiFormatter.COMMANDS} **{self.title}**", ""]
        
        for section_title, items in self.sections:
            if section_title:
                text_parts.append(f"**{section_title}**")
            
            for item_text, _, emoji in items:
                prefix = f"{emoji} " if emoji else "• "
                text_parts.append(f"{prefix}{item_text}")
            
            text_parts.append("")
        
        message_text = "\n".join(text_parts)
        
        # Build keyboard
        buttons = []
        
        for _, items in self.sections:
            # Group items into rows based on columns
            for i in range(0, len(items), columns):
                row = []
                for item_text, callback, emoji in items[i:i+columns]:
                    button_text = f"{emoji} {item_text}" if emoji else item_text
                    row.append(InlineKeyboardButton(button_text, callback_data=callback))
                buttons.append(row)
        
        # Add back button if requested
        if include_back:
            buttons.append([
                InlineKeyboardButton(f"◀️ Back", callback_data=back_callback)
            ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        return message_text, keyboard


class SelectionList:
    """Create selectable lists with checkboxes."""
    
    def __init__(
        self,
        title: str,
        items: List[tuple[str, str, bool]],
        callback_prefix: str = "select"
    ):
        """
        Initialize selection list.
        
        Args:
            title: List title
            items: List of (text, id, selected) tuples
            callback_prefix: Prefix for callback data
        """
        self.title = title
        self.items = items
        self.callback_prefix = callback_prefix
    
    def build(
        self,
        include_done: bool = True,
        done_callback: str = "done"
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Build the selection list.
        
        Args:
            include_done: Whether to include done button
            done_callback: Callback data for done button
        
        Returns:
            Tuple of (message_text, keyboard)
        """
        # Build message text
        text_parts = [f"{EmojiFormatter.COMMANDS} **{self.title}**", ""]
        
        for item_text, _, selected in self.items:
            checkbox = "☑️" if selected else "☐"
            text_parts.append(f"{checkbox} {item_text}")
        
        message_text = "\n".join(text_parts)
        
        # Build keyboard
        buttons = []
        
        for item_text, item_id, selected in self.items:
            checkbox = "☑️" if selected else "☐"
            button_text = f"{checkbox} {item_text}"
            callback = f"{self.callback_prefix}_{item_id}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback)])
        
        # Add done button if requested
        if include_done:
            buttons.append([
                InlineKeyboardButton(f"{EmojiFormatter.SUCCESS} Done", callback_data=done_callback)
            ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        return message_text, keyboard


class ProgressIndicator:
    """Create progress indicators for long operations."""
    
    @staticmethod
    def create(
        title: str,
        current: int,
        total: int,
        status: str = "",
        show_percentage: bool = True,
        show_bar: bool = True
    ) -> str:
        """
        Create a progress indicator message.
        
        Args:
            title: Progress title
            current: Current progress value
            total: Total value
            status: Optional status message
            show_percentage: Whether to show percentage
            show_bar: Whether to show progress bar
        
        Returns:
            Formatted progress message
        """
        parts = [f"{EmojiFormatter.PENDING} **{title}**", ""]
        
        if show_bar:
            # Create progress bar
            bar_width = 10
            filled = int((current / total) * bar_width) if total > 0 else 0
            empty = bar_width - filled
            bar = "█" * filled + "░" * empty
            parts.append(bar)
        
        if show_percentage:
            percentage = int((current / total) * 100) if total > 0 else 0
            parts.append(f"{current}/{total} ({percentage}%)")
        else:
            parts.append(f"{current}/{total}")
        
        if status:
            parts.append("")
            parts.append(status)
        
        return "\n".join(parts)
    
    @staticmethod
    def create_spinner(
        title: str,
        status: str = "Processing...",
        step: int = 0
    ) -> str:
        """
        Create a spinner animation message.
        
        Args:
            title: Spinner title
            status: Status message
            step: Animation step (0-3)
        
        Returns:
            Formatted spinner message
        """
        spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinners[step % len(spinners)]
        
        return f"{spinner} **{title}**\n\n{status}"


# Convenience functions
def create_paginator(
    items: List[Any],
    items_per_page: int = 10
) -> Paginator:
    """Create a paginator with default config."""
    config = PaginationConfig(items_per_page=items_per_page)
    return Paginator(items, config)


def create_confirmation(
    title: str,
    message: str,
    warning: bool = False
) -> tuple[str, InlineKeyboardMarkup]:
    """Create a simple confirmation dialog."""
    return ConfirmationDialog.create(title, message, warning=warning)


def create_menu(title: str) -> MenuBuilder:
    """Create a menu builder."""
    return MenuBuilder(title)
