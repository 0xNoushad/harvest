"""
Tests for UI Interactive Elements

Tests pagination, confirmations, menus, and other interactive components.
"""

import pytest
from agent.ui.interactive import (
    Paginator, PaginationConfig, ConfirmationDialog, MenuBuilder,
    SelectionList, ProgressIndicator, create_paginator, create_confirmation,
    create_menu
)


class TestPaginator:
    """Test pagination functionality."""
    
    def test_paginator_initialization(self):
        """Test paginator initializes correctly."""
        items = list(range(25))
        paginator = Paginator(items)
        
        assert paginator.total_items == 25
        assert paginator.total_pages == 3  # 10 items per page by default
    
    def test_get_page_first(self):
        """Test getting first page."""
        items = list(range(25))
        paginator = Paginator(items)
        
        page_items = paginator.get_page(1)
        assert len(page_items) == 10
        assert page_items[0] == 0
        assert page_items[-1] == 9
    
    def test_get_page_last(self):
        """Test getting last page."""
        items = list(range(25))
        paginator = Paginator(items)
        
        page_items = paginator.get_page(3)
        assert len(page_items) == 5  # Last page has 5 items
        assert page_items[0] == 20
        assert page_items[-1] == 24
    
    def test_get_page_info(self):
        """Test page info generation."""
        items = list(range(25))
        paginator = Paginator(items)
        
        info = paginator.get_page_info(1)
        assert "Page 1 of 3" in info
        assert "1-10 of 25" in info
    
    def test_get_keyboard(self):
        """Test pagination keyboard generation."""
        items = list(range(25))
        paginator = Paginator(items)
        
        keyboard = paginator.get_keyboard(2)
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) > 0
    
    def test_format_page(self):
        """Test page formatting."""
        items = ["Item A", "Item B", "Item C"]
        paginator = Paginator(items)
        
        def formatter(item, idx):
            return f"{idx+1}. {item}"
        
        result = paginator.format_page(1, formatter, header="My Items")
        assert "My Items" in result
        assert "Item A" in result
        assert "Page 1 of 1" in result
    
    def test_custom_items_per_page(self):
        """Test custom items per page."""
        items = list(range(25))
        config = PaginationConfig(items_per_page=5)
        paginator = Paginator(items, config)
        
        assert paginator.total_pages == 5
        page_items = paginator.get_page(1)
        assert len(page_items) == 5


class TestConfirmationDialog:
    """Test confirmation dialog creation."""
    
    def test_create_basic_confirmation(self):
        """Test basic confirmation dialog."""
        text, keyboard = ConfirmationDialog.create(
            title="Confirm Action",
            message="Are you sure?"
        )
        
        assert "Confirm Action" in text
        assert "Are you sure?" in text
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2  # Confirm and Cancel rows
    
    def test_create_with_warning(self):
        """Test confirmation with warning."""
        text, keyboard = ConfirmationDialog.create(
            title="Delete Item",
            message="This cannot be undone",
            warning=True
        )
        
        assert "⚠️" in text or "Delete Item" in text
    
    def test_create_with_details(self):
        """Test confirmation with details."""
        details = {"Amount": "1.5 SOL", "Address": "ABC...XYZ"}
        text, keyboard = ConfirmationDialog.create(
            title="Confirm Withdrawal",
            message="Please review",
            details=details
        )
        
        assert "Amount" in text
        assert "1.5 SOL" in text
    
    def test_create_yes_no(self):
        """Test yes/no confirmation."""
        text, keyboard = ConfirmationDialog.create_yes_no(
            title="Continue?",
            message="Do you want to proceed?"
        )
        
        assert "Continue?" in text
        assert keyboard is not None
    
    def test_create_multi_option(self):
        """Test multi-option dialog."""
        options = [
            ("Option 1", "opt1"),
            ("Option 2", "opt2"),
            ("Option 3", "opt3")
        ]
        text, keyboard = ConfirmationDialog.create_multi_option(
            title="Choose Option",
            message="Select one",
            options=options
        )
        
        assert "Choose Option" in text
        assert len(keyboard.inline_keyboard) == 3


class TestMenuBuilder:
    """Test menu builder functionality."""
    
    def test_menu_initialization(self):
        """Test menu builder initializes."""
        menu = MenuBuilder("Main Menu")
        assert menu.title == "Main Menu"
        assert len(menu.sections) == 0
    
    def test_add_section(self):
        """Test adding section to menu."""
        menu = MenuBuilder("Main Menu")
        menu.add_section("Section 1", [("Item 1", "item1", None)])
        
        assert len(menu.sections) == 1
        assert menu.sections[0][0] == "Section 1"
    
    def test_add_item(self):
        """Test adding item to menu."""
        menu = MenuBuilder("Main Menu")
        menu.add_section()
        menu.add_item("Item 1", "item1", "🔹")
        
        assert len(menu.sections[0][1]) == 1
    
    def test_build_menu(self):
        """Test building complete menu."""
        menu = MenuBuilder("Main Menu")
        menu.add_section("Actions", [
            ("Action 1", "act1", "🔹"),
            ("Action 2", "act2", "🔹")
        ])
        
        text, keyboard = menu.build()
        
        assert "Main Menu" in text
        assert keyboard is not None
    
    def test_build_with_back_button(self):
        """Test building menu with back button."""
        menu = MenuBuilder("Settings")
        menu.add_item("Option 1", "opt1")
        
        text, keyboard = menu.build(include_back=True)
        
        assert len(keyboard.inline_keyboard) >= 2  # At least items + back


class TestSelectionList:
    """Test selection list functionality."""
    
    def test_selection_list_initialization(self):
        """Test selection list initializes."""
        items = [
            ("Item 1", "id1", False),
            ("Item 2", "id2", True)
        ]
        selection = SelectionList("Select Items", items)
        
        assert selection.title == "Select Items"
        assert len(selection.items) == 2
    
    def test_build_selection_list(self):
        """Test building selection list."""
        items = [
            ("Item 1", "id1", False),
            ("Item 2", "id2", True)
        ]
        selection = SelectionList("Select Items", items)
        
        text, keyboard = selection.build()
        
        assert "Select Items" in text
        assert "☑️" in text  # Selected checkbox
        assert "☐" in text   # Unselected checkbox
    
    def test_build_without_done_button(self):
        """Test building without done button."""
        items = [("Item 1", "id1", False)]
        selection = SelectionList("Select", items)
        
        text, keyboard = selection.build(include_done=False)
        
        assert len(keyboard.inline_keyboard) == 1  # Only item, no done


class TestProgressIndicator:
    """Test progress indicator functionality."""
    
    def test_create_progress_basic(self):
        """Test basic progress indicator."""
        result = ProgressIndicator.create(
            title="Processing",
            current=50,
            total=100
        )
        
        assert "Processing" in result
        assert "50/100" in result
        assert "50%" in result
    
    def test_create_progress_with_bar(self):
        """Test progress with bar."""
        result = ProgressIndicator.create(
            title="Loading",
            current=75,
            total=100,
            show_bar=True
        )
        
        assert "█" in result  # Filled bar
        assert "░" in result  # Empty bar
    
    def test_create_progress_with_status(self):
        """Test progress with status message."""
        result = ProgressIndicator.create(
            title="Uploading",
            current=30,
            total=100,
            status="Uploading files..."
        )
        
        assert "Uploading files..." in result
    
    def test_create_spinner(self):
        """Test spinner creation."""
        result = ProgressIndicator.create_spinner(
            title="Loading",
            status="Please wait",
            step=0
        )
        
        assert "Loading" in result
        assert "Please wait" in result


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_paginator_convenience(self):
        """Test create_paginator convenience function."""
        items = list(range(25))
        paginator = create_paginator(items, items_per_page=5)
        
        assert paginator.total_pages == 5
    
    def test_create_confirmation_convenience(self):
        """Test create_confirmation convenience function."""
        text, keyboard = create_confirmation(
            title="Confirm",
            message="Are you sure?"
        )
        
        assert "Confirm" in text
        assert keyboard is not None
    
    def test_create_menu_convenience(self):
        """Test create_menu convenience function."""
        menu = create_menu("Test Menu")
        
        assert menu.title == "Test Menu"
        assert isinstance(menu, MenuBuilder)
