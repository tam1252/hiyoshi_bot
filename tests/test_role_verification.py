import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import asyncio

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui import VerificationView
from src.sheets import SheetManager

class TestRoleVerification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_client = MagicMock()
        self.mock_sheet_manager = MagicMock()
        self.mock_client.sheet_manager = self.mock_sheet_manager
        
        self.data = {'date': '2026-02-11', 'title': 'Test Song', 'score': 1234}
        self.username = "TestUser"
        self.image_url = "http://example.com/image.jpg"

    async def test_verification_view_init(self):
        # View init requires running loop which IsolatedAsyncioTestCase provides
        
        # Test initialization with is_qualifier=True
        view = VerificationView(self.data, self.username, self.mock_client, self.image_url, is_qualifier=True)
        self.assertTrue(view.is_qualifier)

        # Test initialization with is_qualifier=False (default)
        view = VerificationView(self.data, self.username, self.mock_client, self.image_url)
        self.assertFalse(view.is_qualifier)

    async def test_sheet_manager_append_score(self):
        # Mock the workbook and sheet
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.sheet1 = mock_sheet
        
        sm = SheetManager()
        sm.workbook = mock_workbook
        sm.sheet = mock_sheet
        
        # Test 1: is_qualifier=True
        sm.append_score(self.data, self.username, is_qualifier=True)
        # Expected row: [date, username, title, score, True]
        expected_row_true = ['2026-02-11', 'TestUser', 'Test Song', 1234, True]
        mock_sheet.append_row.assert_called_with(expected_row_true)
        
        # Test 2: is_qualifier=False
        sm.append_score(self.data, self.username, is_qualifier=False)
        expected_row_false = ['2026-02-11', 'TestUser', 'Test Song', 1234, False]
        mock_sheet.append_row.assert_called_with(expected_row_false)

if __name__ == '__main__':
    unittest.main()
